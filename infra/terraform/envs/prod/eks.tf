# EKS + 관리형 노드 그룹. Karpenter 대신 Cluster Autoscaler(addons.tf) — 애드온을 줄인다 (§20-6)

locals {
  cluster_name  = "beyondfacade"
  app_namespace = "beyondfacade"
  gitops_repo   = "https://github.com/beyondfacade/cloud.beyondfacade.git" # public — Argo CD가 인증 없이 읽는다
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

  eks_managed_node_groups = merge({
    api = {
      ami_type       = "AL2023_ARM_64_STANDARD"
      instance_types = [var.node_instance_type]
      min_size       = var.node_min_size
      max_size       = var.node_max_size
      desired_size   = var.node_min_size

      use_custom_launch_template = false
      disk_size                  = 20
    }
    }, var.gpu_node ? {
    # 12차 부하 테스트(GPU 임베딩) 동안만 — 노드 그룹 자체를 만들고 지운다. 모듈이 desired를 무시해서(ignore_changes)
    # "평소 0대 → min=max=1"로 올리면 desired 0 < min 1 검증에 걸린다. x86이라 API·CronJob(arm64)은 taint로 막는다
    gpu = {
      ami_type       = "AL2023_x86_64_NVIDIA" # 드라이버·컨테이너 런타임 포함, 쿠버네티스 GPU 인식은 device plugin(addons.tf)
      instance_types = ["g4dn.xlarge"]        # T4 16GB, 서울 $0.647/시간 — 할당량 "G and VT" 4 vCPU 필요
      min_size       = 1
      max_size       = 1
      desired_size   = 1

      use_custom_launch_template = false
      disk_size                  = 60 # CUDA판 Ollama 이미지 + 모델

      labels = { "nvidia.com/gpu.present" = "true" } # device plugin 차트 기본 affinity가 이 라벨을 본다
      taints = { gpu = { key = "nvidia.com/gpu", value = "true", effect = "NO_SCHEDULE" } }
    }
  } : {})
}
