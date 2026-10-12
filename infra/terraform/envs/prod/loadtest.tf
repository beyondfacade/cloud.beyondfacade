# 11차 부하 테스트용 k6 EC2 — 테스트 기간에만 켠다(terraform.tfvars의 loadtest_runner = true). serverplan §20-4·§21-8
# 같은 리전에서 운영 주소(https://api.beyondfacade.cloud)를 친다 — 실제 사용자처럼 ALB·TLS를 거친다.
# 들어오는 포트는 없다(SSH 없음). 명령은 SSM send-command로 보내고, 결과는 데이터 버킷 loadtest/에 올린다(scripts/load/aws.sh).
# public 서브넷 + 공인 IP: private에 두면 트래픽이 NAT를 지나 GB당 처리 요금이 붙고 NAT 대역폭이 측정을 제한한다.

resource "aws_iam_role" "loadtest" {
  count = var.loadtest_runner ? 1 : 0
  name  = "beyondfacade-loadtest"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "loadtest_ssm" {
  count      = var.loadtest_runner ? 1 : 0
  role       = aws_iam_role.loadtest[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "loadtest_results" {
  count = var.loadtest_runner ? 1 : 0
  role  = aws_iam_role.loadtest[0].id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "s3:PutObject", Resource = "${aws_s3_bucket.data.arn}/loadtest/*" }]
  })
}

resource "aws_iam_instance_profile" "loadtest" {
  count = var.loadtest_runner ? 1 : 0
  name  = "beyondfacade-loadtest"
  role  = aws_iam_role.loadtest[0].name
}

resource "aws_security_group" "loadtest" {
  count  = var.loadtest_runner ? 1 : 0
  name   = "beyondfacade-loadtest"
  vpc_id = module.vpc.vpc_id
}

resource "aws_vpc_security_group_egress_rule" "loadtest_all" {
  count             = var.loadtest_runner ? 1 : 0
  security_group_id = aws_security_group.loadtest[0].id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

data "aws_ssm_parameter" "al2023_arm64" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

resource "aws_instance" "loadtest" {
  count                       = var.loadtest_runner ? 1 : 0
  ami                         = data.aws_ssm_parameter.al2023_arm64.value
  instance_type               = var.loadtest_instance_type
  subnet_id                   = module.vpc.public_subnets[0]
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.loadtest[0].id]
  iam_instance_profile        = aws_iam_instance_profile.loadtest[0].name

  metadata_options { http_tokens = "required" }
  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }

  # k6는 도커 이미지로(로컬 1~10차와 같은 방식), 스크립트·동 목록은 공개 저장소에서
  user_data = <<-EOF
    #!/bin/bash
    set -eux
    dnf install -y docker git
    systemctl enable --now docker
    docker pull grafana/k6
    git clone --depth 1 ${local.gitops_repo} /opt/repo
    # VU 3,000명 = 연결 3,000개 — 나가는 포트·파일 한도가 먼저 바닥나지 않게
    echo 'net.ipv4.ip_local_port_range = 1024 65000' > /etc/sysctl.d/90-k6.conf
    echo 'net.ipv4.tcp_tw_reuse = 1' >> /etc/sysctl.d/90-k6.conf
    sysctl --system
  EOF

  tags = { Name = "beyondfacade-k6" }

  lifecycle { ignore_changes = [ami] } # 최신 AMI가 나와도 테스트 중에 다시 만들지 않는다
}
