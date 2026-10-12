# 이미지 저장소·원천 파일/덤프 버킷·비밀값 금고 (serverplan §5, §6-3)

resource "aws_ecr_repository" "api" {
  name                 = "beyondfacade-api"
  image_tag_mutability = "IMMUTABLE" # 태그 = git SHA — 같은 태그를 덮어쓰지 않는다
  force_delete         = true        # destroy 때 이미지까지 지운다 (§20-7)

  image_scanning_configuration { scan_on_push = true }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "최근 30개만 남긴다"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 30 }
      action       = { type = "expire" }
    }]
  })
}

# data/raw·data/backups·pg_dump 보관. destroy 전에 내용을 비워야 지워진다(실수로 데이터가 사라지지 않게)
resource "aws_s3_bucket" "data" {
  bucket = "beyondfacade-data-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# backend/.env의 키를 담을 빈 껍데기. 값은 사람이 콘솔에서 넣는다 — 코드·state에 비밀값을 두지 않는다 (§10-1)
# External Secrets가 이 JSON의 키마다 Secret `backend-env`의 env로 만든다
resource "aws_secretsmanager_secret" "backend_env" {
  name                    = "beyondfacade/prod/backend-env"
  recovery_window_in_days = 0 # destroy 때 바로 지운다 — 원본은 로컬 backend/.env
}
