# 기본값은 serverplan §20-3 안 1(권장) 사양이다. 부하 테스트 때만 tfvars로 올렸다가 내린다(§20-4).

variable "region" {
  type    = string
  default = "ap-northeast-2"
}

variable "admin_cidrs" {
  description = "kubectl로 EKS API에 붙을 수 있는 IP 대역 (예: [\"1.2.3.4/32\"] — 집·노트북 공인 IP)"
  type        = list(string)
}

variable "alert_email" {
  description = "알람을 받을 메일 (SNS 구독 확인 메일을 한 번 눌러야 받는다)"
  type        = string
}

variable "github_oidc_sub_prefix" {
  description = "배포를 허용할 GitHub 저장소의 OIDC sub 앞부분 — 저장소가 immutable subject 형식(owner@ID/repo@ID)을 쓴다(gh api repos/<repo>/actions/oidc/customization/sub)"
  type        = string
  default     = "repo:beyondfacade@320367866/cloud.beyondfacade@1344487674"
}

variable "api_domain" {
  type    = string
  default = "api.beyondfacade.cloud"
}

variable "kubernetes_version" {
  description = "표준 지원 기간 안의 버전만 쓴다 — 연장 지원은 클러스터 요금이 6배 (1.35 표준 지원 ~2027-02)"
  type        = string
  default     = "1.35"
}

variable "node_instance_type" {
  description = "Graviton(arm64) — 이미지는 linux/arm64로 빌드해야 한다"
  type        = string
  default     = "c7g.large"
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  description = "평소 3 — 상한이 없으면 크레딧이 샌다. 부하 테스트 때만 올린다 (§20-6)"
  type        = number
  default     = 3
}

variable "db_instance_class" {
  type    = string
  default = "db.m7g.large"
}

variable "db_multi_az" {
  description = "예산 때문에 증거가 필요한 기간(부하 테스트 10/14~10/16, 장애 조치 리허설 10/21~10/22)에만 true (§21-8)"
  type        = bool
  default     = true
}

variable "db_deletion_protection" {
  description = "정리 단계(§20-7 3단계)에서 false로 apply한 뒤 destroy"
  type        = bool
  default     = true
}

variable "gpu_node" {
  description = "12차 부하 테스트(GPU 임베딩) 동안만 true — GPU 노드 그룹(g4dn.xlarge 1대)과 NVIDIA device plugin을 만든다. 평소 false면 둘 다 없다(비용 0)"
  type        = bool
  default     = false
}

variable "loadtest_runner" {
  description = "k6용 EC2(loadtest.tf) — 부하 테스트 기간에만 true"
  type        = bool
  default     = false
}

variable "loadtest_instance_type" {
  description = "11-1·11-2는 c7g.xlarge, 11-3(VU 3,000명)은 c7g.2xlarge (§20-4)"
  type        = string
  default     = "c7g.xlarge"
}

variable "alb_alarms" {
  description = "ALB 알람(monitoring.tf) — ALB는 Ingress가 만든다. 정리 때 Argo CD 앱을 지우기 전에 false로 apply"
  type        = bool
  default     = true
}
