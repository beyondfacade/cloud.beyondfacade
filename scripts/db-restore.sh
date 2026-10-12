#!/usr/bin/env bash
# 로컬 DB → S3 → RDS 복원 → 행수·벡터 표본 비교 (serverplan §15 Phase 2, Phase 6 전환 때 한 번 더)
# 전제: export AWS_PROFILE=beyondfacade, kubectl이 EKS에 붙어 있음,
#       Secrets Manager backend-env에 RDS용 DATABASE_URL을 넣었고 Secret backend-env가 동기화됨
# 덤프는 data/backups/(gitignore)와 S3 데이터 버킷 dumps/에 남는다 — 관리자 기록 등 운영 데이터라 공유하지 않는다.
set -euo pipefail
cd "$(dirname "$0")/.."

NAMESPACE=beyondfacade
LOCAL_DB_CONTAINER=beyondfacade-db
BUCKET=$(terraform -chdir=infra/terraform/envs/prod output -raw data_bucket)
NAME=rds-migrate-$(date +%Y%m%d-%H%M%S)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

echo "1) 로컬 덤프 → data/backups/$NAME.dump"
mkdir -p data/backups
docker exec "$LOCAL_DB_CONTAINER" pg_dump -U beyondfacade -d beyondfacade -Fc > "data/backups/$NAME.dump"
docker exec -i -e DB="postgresql:///beyondfacade?user=beyondfacade" "$LOCAL_DB_CONTAINER" bash -s < scripts/db-report.sh > "$work/local.txt"

echo "2) S3 업로드"
aws s3 cp --no-progress "data/backups/$NAME.dump" "s3://$BUCKET/dumps/$NAME.dump"
url=$(aws s3 presign "s3://$BUCKET/dumps/$NAME.dump" --expires-in 3600)
kubectl create secret generic db-restore-source -n "$NAMESPACE" --from-literal=DUMP_URL="$url" --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap db-restore-scripts -n "$NAMESPACE" \
  --from-file=scripts/db-restore-job.sh --from-file=scripts/db-report.sh --dry-run=client -o yaml | kubectl apply -f -

echo "3) 복원 Job (수 분~수십 분)"
kubectl delete job db-restore -n "$NAMESPACE" --ignore-not-found
kubectl apply -f deploy/k8s-jobs/db-restore.yaml
for _ in $(seq 360); do  # 최대 60분 — 파드가 못 뜨면(이미지·Secret 문제) 무한히 기다리지 않는다
  [ -n "$(kubectl get job db-restore -n "$NAMESPACE" -o jsonpath='{.status.succeeded}{.status.failed}')" ] && break
  sleep 10
done
if [ -z "$(kubectl get job db-restore -n "$NAMESPACE" -o jsonpath='{.status.succeeded}{.status.failed}')" ]; then
  kubectl delete secret db-restore-source -n "$NAMESPACE"
  kubectl get pods -n "$NAMESPACE" -l job-name=db-restore
  echo "60분 안에 끝나지 않았다 — kubectl describe pod -n $NAMESPACE -l job-name=db-restore"
  exit 1
fi
kubectl delete secret db-restore-source -n "$NAMESPACE"  # 미리 서명 URL을 오래 두지 않는다
kubectl logs job/db-restore -n "$NAMESPACE" -c restore > "$work/rds-full.txt"
sed -n '/^== 행수/,/^== 끝/p' "$work/rds-full.txt" > "$work/rds.txt"
grep -E '^== (복원|pgvector)|^pgvector|pg_restore' "$work/rds-full.txt" || true

echo "4) 비교 (왼쪽 로컬, 오른쪽 RDS)"
if diff "$work/local.txt" "$work/rds.txt"; then
  echo "일치 — 테이블 $(grep -c $'\t' "$work/local.txt")개 행수·벡터 표본 모두 같다"
else
  echo "차이 있음 — 덤프 뒤 로컬 크론이 쓴 행이면 정상(전환 때는 로컬 크론을 먼저 멈춘다). 전체 로그: kubectl logs job/db-restore -n $NAMESPACE -c restore"
  exit 1
fi
