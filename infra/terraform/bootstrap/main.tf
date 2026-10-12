# Terraform state 버킷 — envs/prod보다 먼저, 한 번만 만든다 (serverplan §10-2).
# 이 디렉터리 자체의 state는 로컬 파일(gitignore)이다. 버킷 하나뿐이라 잃어도 import로 되살린다.

terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

provider "aws" {
  region = "ap-northeast-2"
  default_tags {
    tags = { Project = "beyondfacade", Env = "prod", Component = "tfstate", ManagedBy = "terraform" }
  }
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "tfstate" {
  bucket = "beyondfacade-tfstate-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "state_bucket" {
  value = aws_s3_bucket.tfstate.bucket
}
