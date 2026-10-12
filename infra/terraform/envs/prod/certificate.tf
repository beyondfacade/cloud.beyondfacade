# api 도메인 HTTPS 인증서. DNS가 Route53이 아니라(§6-3) 검증 레코드는 사람이 DNS에 넣는다 — outputs의 acm_validation_records
# ALB Controller가 Ingress host로 이 인증서를 자동으로 찾는다 (deploy/k8s/api.yaml)

resource "aws_acm_certificate" "api" {
  domain_name       = var.api_domain
  validation_method = "DNS"

  lifecycle { create_before_destroy = true }
}
