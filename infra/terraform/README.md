# infra/terraform — AWS 인프라 (serverplan §10, §20)

`docs/serverplan.md` §20-3 안 1(권장) 사양을 코드로 적은 것이다. **apply하는 순간부터 과금된다(운영 사양 하루 약 $21).**

| 디렉터리 | 만드는 것 | state |
|---|---|---|
| `bootstrap/` | Terraform state 버킷 1개 | 로컬 파일 (gitignore) |
| `envs/prod/` | VPC·NAT, EKS·노드 그룹·애드온 4개, RDS, ECR, S3, Secrets Manager 껍데기, ACM, GitHub OIDC 역할, 알람 | S3 (bootstrap 버킷) |

| 파일 (`envs/prod/`) | 내용 |
|---|---|
| `network.tf` | VPC 2 AZ, public(ALB·NAT)/private(노드·RDS), NAT 1개 |
| `eks.tf` | EKS 1.35, c7g.large(arm64) × 2~3 |
| `addons.tf` | LB Controller·External Secrets·metrics-server·Cluster Autoscaler + Pod Identity 권한 |
| `database.tf` | RDS PostgreSQL 17 db.m7g.large Multi-AZ, 노드에서만 5432 |
| `storage.tf` | ECR `beyondfacade-api`, S3 데이터 버킷, Secrets Manager `beyondfacade/prod/backend-env` |
| `certificate.tf` | ACM 인증서 `api.beyondfacade.cloud` |
| `github_actions.tf` | main 브랜치 워크플로만 ECR 푸시·EKS 조회 |
| `monitoring.tf` | RDS CPU·디스크 알람 → 메일 (예산·Cost Explorer는 조직 SCP가 막아 없음) |

## 처음 한 번 — 준비

1. 도구: AWS CLI v2, Terraform 1.10 이상, kubectl
2. 관리자 IAM 사용자(MFA 등록)로 `aws configure --profile beyondfacade` → `aws sts get-caller-identity --profile beyondfacade`로 확인
3. **비용은 이 계정에서 안 보인다** — 조직(Organizations) SCP가 Budgets·Cost Explorer·결제 데이터를 막는다(10/12 확인). 실제 비용·남은 크레딧은 팀장을 통해 조직 관리 계정(부트캠프 쪽)에 묻고, 평소엔 **매일 `python3 scripts/aws-cost-estimate.py`**(켜진 리소스 × 서울 공시 단가 → 시간당·하루·14일, 같은 계정의 다른 프로젝트 몫도 따로)로 어림한다 — 안 1 사양이면 하루 약 $20 + 로그 수집

## 만들기 (serverplan §20-5 D1)

```bash
export AWS_PROFILE=beyondfacade         # Terraform·kubectl이 이 프로필의 키를 쓴다

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

1. **메일 확인** — SNS 구독 확인 링크를 누른다(안 누르면 알람이 안 온다)
2. **인증서 검증** — `terraform output acm_validation_records`의 CNAME을 **가비아 DNS**(beyondfacade.cloud 네임서버)에 넣는다. 몇 분 뒤 ACM 콘솔에서 "발급됨"
3. **비밀값 넣기** — `deploy/k8s/external-secret.yaml`이 이 값을 Secret `backend-env`로 옮긴다. Secrets Manager 콘솔 → `beyondfacade/prod/backend-env` → 값 편집 → 키/값으로 하나씩 입력(파일 업로드 금지)
   | 넣는 것 | 키 |
   |---|---|
   | 새 값 | `DATABASE_URL` (아래) |
   | `backend/.env`에서 그대로 (14개) | `GEMINI_API_KEY` `ANTHROPIC_API_KEY`(리포트 폴백 Opus — Gemini 실패 때만 과금, Anthropic 콘솔에 월 한도) `GOOGLE_CLIENT_ID` `GOOGLE_CLIENT_SECRET` `DATA_GO_KR_API_KEY` `SEOUL_OPEN_DATA_API_KEY` `ECOS_API_KEY` `RONE_API_KEY` `VWORLD_API_KEY` `CHILDCARE_API_KEY` `SGIS_SERVICE_ID` `SGIS_SECURITY_KEY` `NAVER_NCP_API_KEY_ID` `NAVER_NCP_API_KEY` |
   | 넣지 않음 | `NEO4J_*`·`REDIS_URL`(코드 미사용), `KOSIS_API_KEY`·`BIZINFO_API_KEY`·`YOUTHCENTER_API_KEY`(코드가 안 읽음), `ADMIN_COOKIE_SECURE`·`GOOGLE_REDIRECT_URI`(비밀 아님 — ConfigMap `deploy/k8s/config.yaml`) |

   `DATABASE_URL`:
   ```
   postgresql+psycopg://beyondfacade:<비밀번호>@<rds_endpoint>:5432/beyondfacade
   ```
   비밀번호는 `terraform output rds_master_secret_arn`의 비밀에 있다. 특수문자가 있으면 URL 인코딩한다
4. **kubectl 연결** — `$(terraform output -raw kubeconfig_command)` → `kubectl get nodes`에 노드 2대

## 앱 배포 (serverplan §13-1)

| 누가 | 언제 | 무엇을 |
|---|---|---|
| GitHub Actions `backend-deploy` | main에 `backend/`·`data/geojson/`이 바뀔 때(또는 Actions 탭에서 수동 실행) | arm64 이미지 빌드(태그 = git SHA) → ECR 푸시 → **DB 마이그레이션**(새 이미지로 Job `alembic upgrade head`, 실패하면 여기서 멈춤) → API·CronJob **이미지만** 교체, 실패하면 이전 버전으로 되돌림 |
| 관리자(Terraform apply한 사람) | 첫 배포, `deploy/k8s` 매니페스트가 바뀔 때 | `scripts/k8s-apply.sh` — 매니페스트 전체 적용, 이미지는 지금 것을 유지 |

CI 역할은 `beyondfacade` 네임스페이스 안 Edit 권한뿐이라 매니페스트 전체(Namespace·ExternalSecret 등)는 사람이 적용한다.

처음 한 번:
1. GitHub 저장소 → Settings → Secrets and variables → Actions → **Variables**에 `AWS_DEPLOY_ROLE_ARN` = `terraform output -raw github_actions_role_arn` (비어 있으면 워크플로가 건너뛴다 — 정리 뒤엔 지운다)
2. Actions → backend-deploy → Run workflow → 이미지가 올라간다(아직 API가 없어 교체 단계는 안내만 남기고 끝난다). 로그의 이미지 주소를 복사
3. `scripts/k8s-apply.sh <이미지 주소>` → `kubectl get pods -n beyondfacade`

## DB 옮기기 (serverplan §15 Phase 2, 전환 때 한 번 더)

비밀값 입력(위 3번)과 kubectl 연결(4번) 뒤, 저장소 루트에서:

```bash
scripts/db-restore.sh
```

로컬 `pg_dump -Fc`(약 160MB) → S3 `dumps/` → 일회성 Job `db-restore`(`deploy/k8s-jobs/`)가 RDS에 `pg_restore --clean --if-exists` → `ANALYZE` → 테이블별 행수·벡터 검색 표본을 로컬과 diff. "일치"가 나오면 끝이다. 다시 돌려도 덮어쓴다(10/12 로컬 리허설: 복원 20초, 49개 테이블 일치, 재복원도 일치).
덤프에는 관리자 기록 등 운영 데이터가 들어 있다 — `data/backups/`(gitignore)와 비공개 S3에만 둔다.

## 이 코드 밖에서 남은 일 (serverplan §15 Phase 2~4)

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

그다음 남은 리소스가 없는지 리전별로 본다(EC2·EBS·EIP·LB·NAT·RDS·스냅샷·로그 그룹, §20-7 4단계). 비용 0 확인은 팀장에게 부탁한다.
