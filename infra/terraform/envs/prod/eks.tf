# EKS + 관리형 노드 그룹. Karpenter 대신 Cluster Autoscaler(addons.tf) — 애드온을 줄인다 (§20-6)

locals {
  cluster_name  = "beyondfacade"
  app_namespace = "beyondfacade"
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  name               = local.cluster_name
  kubernetes_version = var.kubernetes_version
  upgrade_policy     = { support_type = "STANDARD" } # 표준 지원이 끝나도 연장 지원(6배 요금)으로 넘어가지 않게

  endpoint_public_access       = true
  endpoint_public_access_cidrs = var.admin_cidrs

  # apply한 사람(IAM)에게 클러스터 관리자 권한
  enable_cluster_creator_admin_permissions = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  addons = {
    vpc-cni                = { before_compute = true }
    eks-pod-identity-agent = { before_compute = true } # 애드온 파드가 IAM 역할을 받는 통로 (addons.tf)
    kube-proxy             = {}
    coredns                = {}
  }

  eks_managed_node_groups = {
    api = {
      ami_type       = "AL2023_ARM_64_STANDARD"
      instance_types = [var.node_instance_type]
      min_size       = var.node_min_size
      max_size       = var.node_max_size
      desired_size   = var.node_min_size

      use_custom_launch_template = false
      disk_size                  = 20
    }
  }

  # GitHub Actions 배포 역할은 앱 네임스페이스 안에서만 바꿀 수 있다
  access_entries = {
    github_actions = {
      principal_arn = aws_iam_role.github_actions.arn
      policy_associations = {
        app = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"
          access_scope = { type = "namespace", namespaces = [local.app_namespace] }
        }
      }
    }
  }
}
