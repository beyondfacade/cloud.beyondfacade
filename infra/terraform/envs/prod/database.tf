# RDS PostgreSQL 17 + pgvector — 노드(파드)에서만 접근 (serverplan §6-4, §20-3)
# 복원 뒤 한 번: CREATE EXTENSION vector;  (README 2단계)

resource "aws_db_subnet_group" "main" {
  name       = "beyondfacade"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "db" {
  name   = "beyondfacade-db"
  vpc_id = module.vpc.vpc_id
}

# 파드는 노드의 보안 그룹을 그대로 쓴다(VPC CNI 기본) — ALB → 파드 → RDS 한 방향만.
# 노드 그룹이 기본 런치 템플릿(use_custom_launch_template = false)이라 노드에는 모듈의 node SG가 아니라
# EKS 클러스터 기본 SG만 붙는다(10/12 첫 접속 실패로 확인) — 그 SG를 허용한다
resource "aws_vpc_security_group_ingress_rule" "db_from_nodes" {
  security_group_id            = aws_security_group.db.id
  referenced_security_group_id = module.eks.cluster_primary_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_db_instance" "main" {
  identifier     = "beyondfacade"
  engine         = "postgres"
  engine_version = "17"
  instance_class = var.db_instance_class
  multi_az       = var.db_multi_az

  allocated_storage     = 20 # 지금 DB 3.2GB
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "beyondfacade"
  username = "beyondfacade"
  # 비밀번호는 RDS가 만들어 Secrets Manager에 둔다(state·저장소에 안 남는다). DATABASE_URL을 만들 때 꺼내 쓴다
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]

  backup_retention_period      = 7 # 시점 복원(PITR) 리허설용 (§20-4)
  performance_insights_enabled = true

  deletion_protection = var.db_deletion_protection
  skip_final_snapshot = true # 정리 때는 pg_dump로 대신 받는다 (§20-7 2단계)
  apply_immediately   = true # 클래스 변경(부하 테스트 단계)을 바로 적용
}
