# 알람 → SNS → 메일 (serverplan §11-2)
# 예산(Budgets)·Cost Explorer는 넣지 않는다 — 이 계정은 조직(Organizations) SCP가 막는다(10/12 확인). 비용은 조직 관리자 쪽에서 본다
# ALB 알람은 ALB를 Ingress가 만들어 이름을 미리 모른다 — LB Controller가 붙이는 태그로 찾는다(아래 data).
# 정리 때 Argo CD 앱(→ ALB)을 지우기 전에 alb_alarms = false로 apply한다 — 안 그러면 다음 plan이 ALB를 못 찾아 멈춘다(README 지우기 ①)

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

data "aws_lb" "api" {
  count = var.alb_alarms ? 1 : 0
  tags  = { "elbv2.k8s.aws/cluster" = local.cluster_name, "ingress.k8s.aws/stack" = "${local.app_namespace}/api" }
}

data "aws_lb_target_group" "api" {
  count = var.alb_alarms ? 1 : 0
  tags  = { "elbv2.k8s.aws/cluster" = local.cluster_name, "ingress.k8s.aws/resource" = "${local.app_namespace}/api-api:80" }
}

locals {
  alb_dimensions = var.alb_alarms ? { LoadBalancer = data.aws_lb.api[0].arn_suffix } : {}
}

# §11-2: 5분간 5xx 비율 > 1% (ALB 자체 + 파드). 요청이 20건 미만이면 1건만 실패해도 울리니 0으로 본다
resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  count               = var.alb_alarms ? 1 : 0
  alarm_name          = "beyondfacade-alb-5xx-rate"
  alarm_description   = "5분간 5xx 비율(%) > 1"
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  metric_query {
    id          = "rate"
    expression  = "IF(req >= 20, 100 * (FILL(elb5xx, 0) + FILL(target5xx, 0)) / req, 0)"
    return_data = true
  }
  dynamic "metric_query" {
    for_each = { req = "RequestCount", elb5xx = "HTTPCode_ELB_5XX_Count", target5xx = "HTTPCode_Target_5XX_Count" }
    content {
      id = metric_query.key
      metric {
        namespace   = "AWS/ApplicationELB"
        metric_name = metric_query.value
        dimensions  = local.alb_dimensions
        stat        = "Sum"
        period      = 300
      }
    }
  }
}

# §11-2: 응답 시간 p95 > 500ms 10분 지속. 요청이 적은 시간엔 한두 건이 p95를 정해 버려서 5분 100건 이상일 때만 본다
resource "aws_cloudwatch_metric_alarm" "alb_latency" {
  count               = var.alb_alarms ? 1 : 0
  alarm_name          = "beyondfacade-alb-p95-slow"
  alarm_description   = "응답 시간 p95(초) > 0.5, 10분"
  evaluation_periods  = 2
  threshold           = 0.5
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  metric_query {
    id          = "slow"
    expression  = "IF(req >= 100, p95, 0)"
    return_data = true
  }
  metric_query {
    id = "p95"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "TargetResponseTime"
      dimensions  = local.alb_dimensions
      stat        = "p95"
      period      = 300
    }
  }
  metric_query {
    id = "req"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "RequestCount"
      dimensions  = local.alb_dimensions
      stat        = "Sum"
      period      = 300
    }
  }
}

# §11-2: 정상 파드 < 2 (평소 최소 2개, 롤링 배포도 maxUnavailable 0)
resource "aws_cloudwatch_metric_alarm" "alb_healthy" {
  count               = var.alb_alarms ? 1 : 0
  alarm_name          = "beyondfacade-alb-healthy-low"
  alarm_description   = "ALB 정상 대상(파드) < 2, 2분"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HealthyHostCount"
  dimensions          = { LoadBalancer = data.aws_lb.api[0].arn_suffix, TargetGroup = data.aws_lb_target_group.api[0].arn_suffix }
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 2
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching" # 지표가 끊기면 ALB나 대상 그룹이 사라진 것
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}
