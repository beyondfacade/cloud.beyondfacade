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

variable "github_repo" {
  description = "이미지 푸시·배포를 허용할 GitHub 저장소 (owner/name)"
  type        = string
  default     = "beyondfacade/cloud.beyondfacade"
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
  description = "예산이 모자라면 장애 조치 증거가 필요한 기간(10/16~10/22)에만 true (§20-3)"
  type        = bool
  default     = true
}

variable "db_deletion_protection" {
  description = "정리 단계(§20-7 3단계)에서 false로 apply한 뒤 destroy"
  type        = bool
  default     = true
}
