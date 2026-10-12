#!/usr/bin/env bash
# deploy/k8s 매니페스트를 관리자가 적용한다 (serverplan §13-1). 이미지 교체는 CI(backend-deploy)가 한다.
# 이미지는 지금 돌고 있는 것을 유지한다 — 저장소의 kustomization은 계정 ID를 안 넣으려고 자리표시 이름만 갖고 있다.
#   첫 배포:   scripts/k8s-apply.sh <ECR 주소>/beyondfacade-api:<git SHA>   (CI가 올린 이미지)
#   그 뒤:     scripts/k8s-apply.sh
set -euo pipefail

NAMESPACE=beyondfacade
IMAGE=${1:-$(kubectl get deployment api -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}')}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp -r "$(dirname "$0")/../deploy/k8s/." "$tmp"
(cd "$tmp" && kustomize edit set image "beyondfacade-api=$IMAGE")
kubectl apply -k "$tmp"
echo "적용 완료 — 이미지 $IMAGE"
