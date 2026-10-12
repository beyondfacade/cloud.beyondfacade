# VPC 2 AZ — public(ALB·NAT) / private(노드·RDS). NAT는 비용 때문에 1개 (serverplan §6-2, §20-6)

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.0"

  name = "beyondfacade"
  cidr = "10.0.0.0/16"

  azs             = ["${var.region}a", "${var.region}c"]
  public_subnets  = ["10.0.0.0/24", "10.0.1.0/24"]
  private_subnets = ["10.0.16.0/20", "10.0.32.0/20"] # 파드도 VPC IP를 쓴다(VPC CNI) — 넉넉하게

  enable_nat_gateway = true
  single_nat_gateway = true

  # AWS Load Balancer Controller가 ALB를 둘 서브넷을 이 태그로 찾는다
  public_subnet_tags  = { "kubernetes.io/role/elb" = 1 }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = 1 }
}
