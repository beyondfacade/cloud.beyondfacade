# 클러스터 애드온 4개 — Helm으로 클러스터와 함께 설치 (serverplan §10-1, §20-5·§20-6)
#   AWS Load Balancer Controller: Ingress(deploy/k8s/api.yaml) → ALB 생성
#   External Secrets:             Secrets Manager → k8s Secret `backend-env`
#   metrics-server:               HPA가 파드 CPU를 본다
#   Cluster Autoscaler:           파드가 못 뜨면 노드를 늘린다 (max = var.node_max_size)
# 애드온의 AWS 권한은 Pod Identity로 준다 — 키를 파드에 넣지 않는다.
# LB Controller가 먼저다: 모든 Service 생성을 webhook으로 가로채서, 그 파드가 뜨기 전에 다른 차트가 Service를 만들면
# "no endpoints available for service aws-load-balancer-webhook-service"로 실패한다(10/12 첫 apply에서 external-secrets).

module "lb_controller_identity" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "~> 2.0"

  name                            = "aws-load-balancer-controller"
  attach_aws_lb_controller_policy = true
  associations = {
    main = {
      cluster_name    = module.eks.cluster_name
      namespace       = "kube-system"
      service_account = "aws-load-balancer-controller"
    }
  }
}

module "external_secrets_identity" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "~> 2.0"

  name                                  = "external-secrets"
  attach_external_secrets_policy        = true
  external_secrets_secrets_manager_arns = [aws_secretsmanager_secret.backend_env.arn]
  external_secrets_create_permission    = false # 읽기만
  associations = {
    main = {
      cluster_name    = module.eks.cluster_name
      namespace       = "external-secrets"
      service_account = "external-secrets"
    }
  }
}

module "cluster_autoscaler_identity" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "~> 2.0"

  name                             = "cluster-autoscaler"
  attach_cluster_autoscaler_policy = true
  cluster_autoscaler_cluster_names = [module.eks.cluster_name]
  associations = {
    main = {
      cluster_name    = module.eks.cluster_name
      namespace       = "kube-system"
      service_account = "cluster-autoscaler"
    }
  }
}

resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = "3.6.0"
  namespace  = "kube-system"

  values = [yamlencode({
    clusterName    = module.eks.cluster_name
    region         = var.region
    vpcId          = module.vpc.vpc_id
    serviceAccount = { name = "aws-load-balancer-controller" }
  })]

  depends_on = [module.eks, module.lb_controller_identity]
}

resource "helm_release" "external_secrets" {
  name             = "external-secrets"
  repository       = "https://charts.external-secrets.io"
  chart            = "external-secrets"
  version          = "2.12.0"
  namespace        = "external-secrets"
  create_namespace = true

  values = [yamlencode({
    serviceAccount = { name = "external-secrets" }
  })]

  depends_on = [module.eks, module.external_secrets_identity, helm_release.aws_load_balancer_controller]
}

resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server"
  chart      = "metrics-server"
  version    = "3.14.0"
  namespace  = "kube-system"

  depends_on = [module.eks, helm_release.aws_load_balancer_controller]
}

resource "helm_release" "cluster_autoscaler" {
  name       = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"
  chart      = "cluster-autoscaler"
  version    = "9.59.0" # 앱 1.35 — 클러스터 버전과 마이너를 맞춘다
  namespace  = "kube-system"

  values = [yamlencode({
    autoDiscovery = { clusterName = module.eks.cluster_name } # 관리형 노드 그룹 ASG에 붙는 태그로 찾는다
    awsRegion     = var.region
    rbac          = { serviceAccount = { name = "cluster-autoscaler" } }
    extraArgs     = { "balance-similar-node-groups" = true, "scale-down-unneeded-time" = "5m" }
  })]

  depends_on = [module.eks, module.cluster_autoscaler_identity, helm_release.aws_load_balancer_controller]
}
