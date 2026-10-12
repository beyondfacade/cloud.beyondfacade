# infra/terraform — AWS 인프라 (serverplan §10, §20)

`docs/serverplan.md` §20-3 안 1(권장) 사양을 코드로 적은 것이다. **apply하는 순간부터 과금된다(운영 사양 하루 약 $21).**

| 디렉터리 | 만드는 것 | state |
|---|---|---|
| `bootstrap/` | Terraform state 버킷 1개 | 로컬 파일 (gitignore) |
| `envs/prod/` | VPC·NAT, EKS·노드 그룹·애드온 4개, RDS, ECR, S3, Secrets Manager 껍데기, ACM, GitHub OIDC 역할, 알람·예산 | S3 (bootstrap 버킷) |

| 파일 (`envs/prod/`) | 내용 |
|---|---|
| `network.tf` | VPC 2 AZ, public(ALB·NAT)/private(노드·RDS), NAT 1개 |
| `eks.tf` | EKS 1.35, c7g.large(arm64) × 2~3 |
| `addons.tf` | LB Controller·External Secrets·metrics-server·Cluster Autoscaler + Pod Identity 권한 |
| `database.tf` | RDS PostgreSQL 17 db.m7g.large Multi-AZ, 노드에서만 5432 |
| `storage.tf` | ECR `beyondfacade-api`, S3 데이터 버킷, Secrets Manager `beyondfacade/prod/backend-env` |
| `certificate.tf` | ACM 인증서 `api.beyondfacade.cloud` |
| `github_actions.tf` | main 브랜치 워크플로만 ECR 푸시·EKS 조회 |
| `monitoring.tf` | RDS CPU·디스크 알람 → 메일, 월 예산 $200·$300·$350·예측 $400 경보 |

## 처음 한 번 — 준비

1. 도구: AWS CLI v2, Terraform 1.10 이상, kubectl
2. AWS 계정 루트에 MFA. 루트 말고 관리자 IAM 사용자(또는 SSO)로 `aws configure` → `aws sts get-caller-identity`로 확인
3. **크레딧 약관 확인** — 적용 제외 서비스·만료일 (serverplan §20-8)

## 만들기 (serverplan §20-5 D1)

```bash
# 1) state 버킷
cd infra/terraform/bootstrap
terraform init && terraform apply          # 출력 state_bucket 기억

# 2) 운영 인프라
cd ../envs/prod
cp terraform.tfvars.example terraform.tfvars   # admin_cidrs·alert_email 채우기
terraform init -backend-config="bucket=<state_bucket>"
terraform plan                              # 무엇이 생기는지 읽는다(전부 "create"여야 한다)
terraform apply                             # 20~30분 (EKS·Multi-AZ RDS가 오래 걸린다)
```

apply가 끝나면 사람이 할 일:

1. **메일 2통 확인** — SNS 구독 확인 링크를 누른다(안 누르면 알람이 안 온다)
2. **인증서 검증** — `terraform output acm_validation_records`의 CNAME을 Cloudflare DNS에 넣는다(프록시 끔, 회색 구름). 몇 분 뒤 ACM 콘솔에서 "발급됨"
3. **비밀값 넣기** — `deploy/k8s/external-secret.yaml`이 이 값을 Secret `backend-env`로 옮긴다. Secrets Manager 콘솔 → `beyondfacade/prod/backend-env` → 값 편집 → 키/값으로 `backend/.env` 항목을 하나씩 입력(파일 업로드 금지). `DATABASE_URL`만 새로 만든다:
   ```
   postgresql+psycopg://beyondfacade:<비밀번호>@<rds_endpoint>:5432/beyondfacade
   ```
   비밀번호는 `terraform output rds_master_secret_arn`의 비밀에 있다. 특수문자가 있으면 URL 인코딩한다
4. **kubectl 연결** — `$(terraform output -raw kubeconfig_command)` → `kubectl get nodes`에 노드 2대

## 이 코드 밖에서 남은 일 (serverplan §15 Phase 2~4)

- 이미지: 노드가 arm64라 `docker buildx build --platform linux/arm64 --build-context geojson=data/geojson backend` → ECR 푸시
- DB 복원: `pg_dump -Fc` → S3 → 클러스터 안 일회성 Job에서 `pg_restore`, `CREATE EXTENSION vector`, 행수 비교
- 앱 네임스페이스는 관리자가 처음 한 번 만든다(GitHub Actions 역할은 `beyondfacade` 네임스페이스 안만 바꿀 수 있다)
- 집 Ollama 연결(Tailscale), ALB 5xx·지연 알람(ALB가 생긴 뒤)

## 바꾸기 — 부하 테스트 단계 (serverplan §20-4)

`terraform.tfvars`에서 `node_max_size`·`db_instance_class`를 올려 `plan` → `apply`, 끝나면 되돌려 다시 `apply`. **콘솔에서 손으로 바꾸지 않는다** — 다음 apply가 되돌린다.

## 지우기 (serverplan §20-7) — 순서가 중요하다

```bash
kubectl delete ingress api -n beyondfacade  # ① ALB부터 — 클러스터를 먼저 지우면 ALB가 고아로 남아 계속 과금
# ② pg_dump를 받아 로컬에서 복원 확인 (§20-7 2단계)
# ③ terraform.tfvars에 db_deletion_protection = false → terraform apply
# ④ S3 데이터 버킷 비우기(버전 포함): 콘솔 → 버킷 → 비우기
terraform destroy
# ⑤ bootstrap도: state 버킷을 비운 뒤 cd ../../bootstrap && terraform destroy
```

그다음 Cost Explorer에서 일 비용이 0인지, 다른 리전에 남은 것이 없는지 본다(§20-7 4단계).
