output "kubeconfig_command" {
  description = "kubectl 연결"
  value       = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.region}"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "rds_master_secret_arn" {
  description = "RDS가 만든 마스터 비밀번호 — DATABASE_URL을 만들 때 꺼낸다"
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
}

output "backend_env_secret_name" {
  value = aws_secretsmanager_secret.backend_env.name
}

output "data_bucket" {
  value = aws_s3_bucket.data.bucket
}

output "acm_validation_records" {
  description = "DNS(Cloudflare)에 CNAME으로 넣는다 — 넣어야 인증서가 발급된다"
  value = [for o in aws_acm_certificate.api.domain_validation_options : {
    name  = o.resource_record_name
    type  = o.resource_record_type
    value = o.resource_record_value
  }]
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}
