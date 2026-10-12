# 알람 → SNS → 메일, 예산 경보 (serverplan §11-2, §20-8)
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

# 크레딧을 빼기 전 금액으로 본다 — 크레딧을 포함하면 비용이 0으로 보여 알람이 안 울린다 (§20-8)
resource "aws_budgets_budget" "monthly" {
  name         = "beyondfacade-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_types {
    include_credit = false
    include_refund = false
  }

  dynamic "notification" {
    for_each = [200, 300, 350]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "ABSOLUTE_VALUE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.alert_email]
    }
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}
