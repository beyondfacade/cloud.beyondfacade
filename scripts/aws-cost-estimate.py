#!/usr/bin/env python3
"""서울 리전에 지금 켜져 있는 리소스로 시간당·하루 비용을 어림한다 (serverplan §20-8 "매일 한 번").

이 계정은 조직 SCP가 Budgets·Cost Explorer·결제 데이터를 막아(10/12 확인) 실제 청구액을 볼 수 없다.
그래서 켜진 리소스 × 공시 단가로 계산한다. 같은 계정의 다른 프로젝트 리소스도 크레딧을 쓰므로 함께 센다.

- 단가: 2026-10-12 AWS Price List API(서울, 온디맨드)에서 뽑은 값. 표에 없는 인스턴스 유형은 "단가 모름"으로 표시
- 빠지는 것(사용량 비례): NAT 처리 GB당 $0.059, ALB LCU, Aurora 서버리스 ACU, S3, 데이터 전송, Gemini(크레딧 밖)
- CloudWatch 로그 수집은 지난 24시간 IncomingBytes × $0.76/GB로 따로 보인다

실행: AWS_PROFILE=beyondfacade python3 scripts/aws-cost-estimate.py
"""

import json
import subprocess
from datetime import datetime, timedelta, timezone

REGION = "ap-northeast-2"
HOURS_PER_MONTH = 730

EC2_HOURLY = {"c7g.large": 0.0816, "c7g.xlarge": 0.1632, "c7g.2xlarge": 0.3264}
RDS_HOURLY = {  # PostgreSQL (단일 AZ, Multi-AZ)
    "db.m7g.large": (0.2344, 0.4688),
    "db.m7g.xlarge": (0.4688, 0.9376),
    "db.m7g.2xlarge": (0.9376, 1.8752),
}
EKS_HOURLY = 0.10
NAT_HOURLY = 0.059
ALB_HOURLY = 0.0225
PUBLIC_IPV4_HOURLY = 0.005
EBS_GP3_GB_MONTH = 0.0912
RDS_GP3_GB_MONTH = (0.131, 0.262)  # 단일 AZ, Multi-AZ
SECRET_MONTH = 0.40
KMS_KEY_MONTH = 1.0
LOG_INGEST_GB = 0.76


def aws(*args: str) -> dict:
    out = subprocess.run(["aws", *args, "--region", REGION, "--output", "json"], capture_output=True, text=True, check=True)
    return json.loads(out.stdout or "{}")


def ours(*names: str) -> bool:
    return any("beyondfacade" in (name or "") for name in names)


def main() -> None:
    lines: list[tuple[bool, str, float | None]] = []  # (우리 것, 설명, 시간당 $ — None이면 단가 모름)

    for cluster in aws("eks", "list-clusters")["clusters"]:
        lines.append((ours(cluster), f"EKS 클러스터 {cluster}", EKS_HOURLY))

    reservations = aws("ec2", "describe-instances", "--filters", "Name=instance-state-name,Values=running")["Reservations"]
    for instance in (i for r in reservations for i in r["Instances"]):
        tags = {t["Key"]: t["Value"] for t in instance.get("Tags", [])}
        kind = instance["InstanceType"]
        name = tags.get("Name") or tags.get("eks:cluster-name") or instance["InstanceId"]
        lines.append((ours(name, tags.get("eks:cluster-name")), f"EC2 {kind} {name}", EC2_HOURLY.get(kind)))

    gp3_gb = sum(v["Size"] for v in aws("ec2", "describe-volumes")["Volumes"])
    if gp3_gb:
        lines.append((True, f"EBS 볼륨 합계 {gp3_gb}GB (gp3 단가)", gp3_gb * EBS_GP3_GB_MONTH / HOURS_PER_MONTH))

    for nat in aws("ec2", "describe-nat-gateways", "--filter", "Name=state,Values=available")["NatGateways"]:
        lines.append((True, f"NAT Gateway {nat['NatGatewayId']} (처리 GB 제외)", NAT_HOURLY))

    for lb in aws("elbv2", "describe-load-balancers")["LoadBalancers"]:
        lines.append((ours(lb["LoadBalancerName"]) or lb["LoadBalancerName"].startswith("k8s-"),
                      f"로드밸런서 {lb['Type']} {lb['LoadBalancerName']} (LCU 제외)",
                      ALB_HOURLY if lb["Type"] == "application" else None))

    interfaces = aws("ec2", "describe-network-interfaces")["NetworkInterfaces"]
    in_use = sum(1 for n in interfaces if n.get("Association", {}).get("PublicIp"))
    idle = sum(1 for a in aws("ec2", "describe-addresses")["Addresses"] if not a.get("AssociationId"))
    if in_use + idle:
        lines.append((True, f"공인 IPv4 {in_use + idle}개 (사용 중 {in_use} · 놀고 있음 {idle})", (in_use + idle) * PUBLIC_IPV4_HOURLY))

    for db in aws("rds", "describe-db-instances")["DBInstances"]:
        name, kind, multi = db["DBInstanceIdentifier"], db["DBInstanceClass"], db["MultiAZ"]
        if kind == "db.serverless":
            lines.append((ours(name), f"RDS {name} Aurora 서버리스 (ACU 사용량 비례 — 계산 제외)", 0.0))
            continue
        price = RDS_HOURLY.get(kind)
        hourly = None if price is None else price[multi] + db["AllocatedStorage"] * RDS_GP3_GB_MONTH[multi] / HOURS_PER_MONTH
        lines.append((ours(name), f"RDS {kind} {'Multi-AZ' if multi else '단일 AZ'} {name} + {db['AllocatedStorage']}GB", hourly))

    secrets = aws("secretsmanager", "list-secrets")["SecretList"]
    if secrets:
        lines.append((True, f"Secrets Manager {len(secrets)}개", len(secrets) * SECRET_MONTH / HOURS_PER_MONTH))

    keys = [aws("kms", "describe-key", "--key-id", k["KeyId"])["KeyMetadata"] for k in aws("kms", "list-keys")["Keys"]]
    customer_keys = [k for k in keys if k["KeyManager"] == "CUSTOMER" and k["KeyState"] == "Enabled"]
    if customer_keys:
        lines.append((True, f"KMS 고객 관리 키 {len(customer_keys)}개", len(customer_keys) * KMS_KEY_MONTH / HOURS_PER_MONTH))

    print(f"== 서울 리전 켜진 리소스 ({datetime.now().astimezone():%Y-%m-%d %H:%M})")
    for mine, label, hourly in lines:
        cost = "단가 모름" if hourly is None else f"${hourly:.4f}/시간"
        print(f"  {'우리' if mine else '다른'}  {label:<60} {cost}")

    for title, pick in (("우리(beyondfacade)", True), ("다른 프로젝트", False)):
        hourly = sum(h for mine, _, h in lines if mine == pick and h is not None)
        print(f"== {title}: 시간당 ${hourly:.3f} · 하루 ${hourly * 24:.2f} · 14일 ${hourly * 24 * 14:.0f}")

    since = datetime.now(timezone.utc) - timedelta(days=1)
    ingested = 0.0
    for group in aws("logs", "describe-log-groups")["logGroups"]:
        stats = aws("cloudwatch", "get-metric-statistics", "--namespace", "AWS/Logs", "--metric-name", "IncomingBytes",
                    "--dimensions", f"Name=LogGroupName,Value={group['logGroupName']}", "--statistics", "Sum",
                    "--start-time", since.isoformat(), "--end-time", datetime.now(timezone.utc).isoformat(), "--period", "86400")
        ingested += sum(p["Sum"] for p in stats["Datapoints"])
    gb = ingested / 1024**3
    print(f"== CloudWatch 로그 수집(지난 24시간): {gb:.2f}GB · ${gb * LOG_INGEST_GB:.2f}")
    print("   빠진 것: NAT 처리 GB·ALB LCU·Aurora ACU·S3·데이터 전송 — 실제 청구는 이보다 조금 많다")


if __name__ == "__main__":
    main()
