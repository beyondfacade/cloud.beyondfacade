terraform {
  required_version = ">= 1.10"

  required_providers {
    aws  = { source = "hashicorp/aws", version = "~> 6.0" }
    helm = { source = "hashicorp/helm", version = "~> 3.0" }
  }

  # bucket은 계정 ID가 들어가 저장소(public)에 적지 않는다:
  #   terraform init -backend-config="bucket=<bootstrap의 state_bucket 출력>"
  backend "s3" {
    key          = "prod/terraform.tfstate"
    region       = "ap-northeast-2"
    encrypt      = true
    use_lockfile = true # S3 네이티브 잠금 — 두 사람이 동시에 apply해 state가 깨지는 것 방지
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = "beyondfacade", Env = "prod", ManagedBy = "terraform" }
  }
}

# 클러스터 애드온(addons.tf)을 설치할 때 쓴다 — 토큰은 aws CLI로 그때그때 받는다
provider "helm" {
  kubernetes = {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    exec = {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name, "--region", var.region]
    }
  }
}

data "aws_caller_identity" "current" {}
