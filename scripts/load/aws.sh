#!/usr/bin/env bash
# 11차 부하 테스트(AWS) — 같은 리전 EC2의 k6로 운영 주소를 치고, 클러스터·ALB·RDS 지표를 한 폴더에 모은다 (serverplan §21-8)
#   scripts/load/aws.sh snapshot                       테스트 전 RDS 수동 스냅샷 (단계마다 한 번)
#   scripts/load/aws.sh stage <이름> <PROFILE> [k6 -e 인자...]   예: stage 11-1 ceiling3k -e LLM=1 -e GZIP=1
#   scripts/load/aws.sh cleanup                        테스트가 남긴 행 지우기 (LLM_MODE=fake 리포트·k6 IP 보안 이벤트)
# stage 순서(run_stage.sh와 같은 조건): pg_stat_statements 초기화 → 30초 안정화 → 모니터(15초) + 원격 k6 → 끝나면
#   느린 쿼리 상위 20 · CloudWatch(ALB·RDS 1분 단위) · k6 결과(S3 loadtest/)를 logs/load/<이름>-<시각>/ 에.
# 전제: terraform.tfvars의 loadtest_runner = true로 EC2가 떠 있고, kubectl context가 이 클러스터. aws CLI는 AWS_PROFILE로.
# 새벽 수집 시간(03:30~06:10 KST)엔 돌리지 않는다 — 수집 CronJob과 섞이면 결과가 흔들린다.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export AWS_REGION=ap-northeast-2
export AWS_PROFILE="${AWS_PROFILE:-beyondfacade}"  # 이 계정의 프로필 — 없으면 NoCredentials
NS=beyondfacade
BASE=https://api.beyondfacade.cloud
TF=infra/terraform/envs/prod

# RDS에 직접 붙을 수 없어서(private) API 파드 안의 psycopg로 SQL을 돌린다 — 연결 문자열은 출력하지 않는다
pg() {
  kubectl -n "$NS" exec -i deploy/api -c api -- python - "$1" <<'PY'
import os, sys, psycopg
url = os.environ["DATABASE_URL"].replace("+psycopg", "", 1)
with psycopg.connect(url, autocommit=True) as conn:
    cur = conn.execute(sys.argv[1])
    if cur.description:
        print("\t".join(d.name for d in cur.description))
        for row in cur:
            print("\t".join("" if v is None else str(v) for v in row))
    else:
        print(cur.statusmessage)
PY
}

instance_id() {
  aws ec2 describe-instances --filters Name=tag:Name,Values=beyondfacade-k6 Name=instance-state-name,Values=running \
    --query 'Reservations[0].Instances[0].InstanceId' --output text
}

bucket() { terraform -chdir="$TF" output -raw data_bucket; }

monitor() {  # 15초마다 HPA·파드 CPU 합·노드 수·Pending 파드
  echo "time,hpa_replicas,hpa_cpu_pct,pods_cpu_m,pods_mem_mi,nodes,pending"
  while true; do
    local hpa top nodes pending
    hpa=$(kubectl -n "$NS" get hpa api -o jsonpath='{.status.currentReplicas},{.status.currentMetrics[0].resource.current.averageUtilization}')
    top=$(kubectl -n "$NS" top pods -l app=api --no-headers 2>/dev/null | awk '{c+=$2; m+=$3} END {print c+0","m+0}')
    nodes=$(kubectl get nodes --no-headers | wc -l)
    pending=$(kubectl -n "$NS" get pods --field-selector=status.phase=Pending --no-headers 2>/dev/null | wc -l)
    echo "$(date +%H:%M:%S),$hpa,$top,$nodes,$pending"
    sleep 15
  done
}

cloudwatch() {  # $1 시작 $2 끝(ISO) $3 출력 파일 — 1분 단위
  local lb tg
  lb=$(aws elbv2 describe-load-balancers --query 'LoadBalancers[?starts_with(LoadBalancerName,`k8s-beyondfa-api`)].LoadBalancerArn' --output text | sed 's|.*:loadbalancer/||')
  tg=$(aws elbv2 describe-target-groups --query 'TargetGroups[?starts_with(TargetGroupName,`k8s-beyondfa-api`)].TargetGroupArn' --output text | sed 's|.*:||')
  python3 - "$lb" "$tg" > "$3.queries.json" <<'PY'
import json, sys
lb, tg = sys.argv[1], sys.argv[2]
alb = [{"Name": "LoadBalancer", "Value": lb}]
rds = [{"Name": "DBInstanceIdentifier", "Value": "beyondfacade"}]
q = [
    ("req", "AWS/ApplicationELB", "RequestCount", alb, "Sum"),
    ("p95", "AWS/ApplicationELB", "TargetResponseTime", alb, "p95"),
    ("p99", "AWS/ApplicationELB", "TargetResponseTime", alb, "p99"),
    ("elb5xx", "AWS/ApplicationELB", "HTTPCode_ELB_5XX_Count", alb, "Sum"),
    ("target5xx", "AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", alb, "Sum"),
    ("healthy", "AWS/ApplicationELB", "HealthyHostCount", alb + [{"Name": "TargetGroup", "Value": tg}], "Minimum"),
    ("db_cpu", "AWS/RDS", "CPUUtilization", rds, "Maximum"),
    ("db_conn", "AWS/RDS", "DatabaseConnections", rds, "Maximum"),
    ("db_read_iops", "AWS/RDS", "ReadIOPS", rds, "Average"),
    ("db_free_mem", "AWS/RDS", "FreeableMemory", rds, "Minimum"),
]
print(json.dumps([{"Id": i, "MetricStat": {"Metric": {"Namespace": ns, "MetricName": m, "Dimensions": d},
                   "Period": 60, "Stat": s}} for i, ns, m, d, s in q]))
PY
  aws cloudwatch get-metric-data --start-time "$1" --end-time "$2" \
    --metric-data-queries "file://$3.queries.json" --output json > "$3"
  rm -f "$3.queries.json"
}

remote_k6() {  # $1 단계 폴더 이름 $2 PROFILE 나머지 = k6 인자. 원격에서 끝날 때까지 기다린다
  local run=$1 profile=$2; shift 2
  local id cmd_id script status
  id=$(instance_id)
  [ "$id" = "None" ] && { echo "k6 EC2가 없다 — terraform.tfvars에 loadtest_runner = true로 apply" >&2; return 1; }
  script=$(cat <<EOF
set -uo pipefail
cd /opt/repo && git pull -q --ff-only
OUT=/opt/results/$run; mkdir -p \$OUT; chmod 777 \$OUT
echo "start \$(date '+%F %T') profile=$profile base=$BASE args=$* \$(docker run --rm grafana/k6 version | head -1)" > \$OUT/meta.txt
docker run --rm --name k6 --network host --ulimit nofile=65536:65536 -v /opt/repo:/w:ro -v \$OUT:/out -w /w grafana/k6 run \
  -e BASE=$BASE -e PROFILE=$profile $* --summary-export /out/summary.json --out csv=/out/raw.csv.gz \
  scripts/load/load.js > \$OUT/k6.txt 2>&1
CODE=\$?
echo "end \$(date '+%F %T') k6_exit=\$CODE" >> \$OUT/meta.txt
aws s3 cp --recursive --quiet \$OUT s3://$(bucket)/loadtest/$run/
tail -30 \$OUT/k6.txt
exit \$CODE
EOF
)
  local params; params=$(mktemp)
  python3 -c 'import json,sys; print(json.dumps({"commands": [sys.argv[1]], "executionTimeout": ["10800"]}))' "$script" > "$params"
  cmd_id=$(aws ssm send-command --instance-ids "$id" --document-name AWS-RunShellScript --timeout-seconds 600 \
    --parameters "file://$params" --query Command.CommandId --output text)
  rm -f "$params"
  echo "원격 k6 시작: $id 명령 $cmd_id"
  while sleep 30; do
    status=$(aws ssm get-command-invocation --command-id "$cmd_id" --instance-id "$id" --query Status --output text 2>/dev/null)
    case "$status" in Pending|InProgress|Delayed|"") continue ;; esac
    break
  done
  echo "원격 k6 끝: $status"
  [ "$status" = Success ]
}

stage() {
  local name=$1 profile=$2; shift 2
  local run="$name-$(date +%m%d-%H%M)" out start end code mon
  out="logs/load/$run"
  mkdir -p "$out"
  pg "create extension if not exists pg_stat_statements" > /dev/null
  pg "select pg_stat_statements_reset()" > /dev/null
  sleep 30
  start=$(date -u +%FT%TZ)
  echo "start $(date '+%F %T') stage=$name profile=$profile base=$BASE args=$* $(kubectl -n "$NS" get deploy api -o jsonpath='{.spec.template.spec.containers[0].image}' | sed 's|.*:||')" > "$out/meta.txt"
  monitor > "$out/monitor.csv" 2>&1 &
  mon=$!
  remote_k6 "$run" "$profile" "$@"
  code=$?
  kill $mon; wait $mon 2>/dev/null
  end=$(date -u +%FT%TZ)
  echo "end $(date '+%F %T') remote_ok=$([ $code = 0 ] && echo yes || echo no)" >> "$out/meta.txt"
  pg "select calls, round(mean_exec_time::numeric,1) mean_ms, round(max_exec_time::numeric,1) max_ms,
    round(total_exec_time::numeric) total_ms, left(regexp_replace(query,'\s+',' ','g'),160) query
    from pg_stat_statements order by total_exec_time desc limit 20" > "$out/pg_top.tsv" 2>&1
  sleep 120  # CloudWatch 1분 지표가 마저 들어오게
  cloudwatch "$start" "$(date -u +%FT%TZ)" "$out/cloudwatch.json"
  aws s3 cp --recursive --quiet "s3://$(bucket)/loadtest/$run/" "$out/k6/"
  kubectl -n "$NS" logs -l app=api --since-time="$start" --tail=-1 --prefix --max-log-requests=30 2>/dev/null | gzip > "$out/api.log.gz"
  echo "$out remote_ok=$([ $code = 0 ] && echo yes || echo no)"
}

cleanup() {
  # LLM_MODE=fake로 만든 리포트는 model='fake'라 실제 리포트와 섞이지 않는다. 보안 이벤트는 k6 EC2 공인 IP로 고른다
  local ip
  ip=$(aws ec2 describe-instances --filters Name=tag:Name,Values=beyondfacade-k6 \
    --query 'Reservations[].Instances[].PublicIpAddress' --output text | tr '\t' '\n' | grep -v None | head -1)
  pg "delete from llm_usage where analysis_id in (select id from analysis_report where model = 'fake')"
  pg "delete from analysis_report where model = 'fake'"
  pg "delete from llm_call_event where model = 'fake'"
  [ -n "$ip" ] && pg "delete from access_event where ip = '$ip'"
  pg "select (select count(*) from analysis_report where model = 'fake') fake_reports,
    (select count(*) from llm_call_event where model = 'fake') fake_calls"
}

snapshot() {
  local id="beyondfacade-before-11-$(date +%m%d-%H%M)"
  aws rds create-db-snapshot --db-instance-identifier beyondfacade --db-snapshot-identifier "$id" \
    --query DBSnapshot.DBSnapshotIdentifier --output text || return 1
  echo "완료까지 몇 분 — aws rds wait db-snapshot-available --db-snapshot-identifier $id"
}

case "${1:-}" in
  stage) shift; stage "$@" ;;
  cleanup) cleanup ;;
  snapshot) snapshot ;;
  *) sed -n '2,9p' "$0"; exit 1 ;;
esac
