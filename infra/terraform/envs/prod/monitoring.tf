# 알람 → SNS → 메일 (serverplan §11-2)
# 예산(Budgets)·Cost Explorer는 넣지 않는다 — 이 계정은 조직(Organizations) SCP가 막는다(10/12 확인). 비용은 조직 관리자 쪽에서 본다
# ALB 5xx·지연 알람은 ALB를 Ingress가 만들어 이름을 미리 모른다 — ALB가 생긴 뒤 추가한다

resource "aws_sns_topic" "alerts" {
  name = "beyondfacade-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "db_cpu" {
  alarm_name          = "beyondfacade-db-cpu-high"
  namespace           = "AWS/RDS"
  metric_name         = "CPUUtilization"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.main.identifier }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "db_storage" {
  alarm_name          = "beyondfacade-db-storage-low"
  namespace           = "AWS/RDS"
  metric_name         = "FreeStorageSpace"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.main.identifier }
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 5 * 1024 * 1024 * 1024 # 5GB
  comparison_operator = "LessThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
