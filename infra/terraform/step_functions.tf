# Step Functions state machine for phase orchestration.
# Discovery → Architecture → POC → Production → Handoff
# Each phase: ECS Swarm → PM Review (Lambda) → Approval Gate (waitForTaskToken)
# Approval decision: APPROVED → next phase | REVISION_REQUESTED → re-run phase

resource "aws_cloudwatch_log_group" "sfn" {
  name              = "/aws/states/cloudcrew-orchestrator"
  retention_in_days = 14

  tags = { Name = "cloudcrew-sfn-logs" }
}

resource "aws_sfn_state_machine" "orchestrator" {
  name     = "cloudcrew-orchestrator-${var.environment}"
  role_arn = aws_iam_role.sfn_execution.arn

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  definition = jsonencode({
    Comment = "CloudCrew phase orchestration — 5 delivery phases with approval gates"
    StartAt = "Discovery"

    States = {
      # =====================================================================
      # DISCOVERY
      # =====================================================================
      Discovery = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"            = "start_phase"
            "project_id.$"      = "$.project_id"
            "phase"             = "DISCOVERY"
            "task_token.$"      = "$$.Task.Token"
            "customer_feedback" = ""
          }
        }
        ResultPath = "$.discovery_result"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 10
          MaxAttempts     = 1
          BackoffRate     = 2.0
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "HandleError"
        }]
        Next = "DiscoveryPMReview"
      }

      DiscoveryPMReview = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.pm_review.arn
          Payload = {
            "project_id.$" = "$.project_id"
            "phase"        = "DISCOVERY"
          }
        }
        ResultPath     = "$.pm_review"
        ResultSelector = { "review_passed.$" = "$.Payload.review_passed" }
        Next           = "DiscoveryApproval"
      }

      DiscoveryApproval = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"       = "store_approval_token"
            "project_id.$" = "$.project_id"
            "phase"        = "DISCOVERY"
            "task_token.$" = "$$.Task.Token"
          }
        }
        ResultPath = "$.approval"
        Next       = "DiscoveryDecision"
      }

      DiscoveryDecision = {
        Type = "Choice"
        Choices = [{
          Variable     = "$.approval.decision"
          StringEquals = "APPROVED"
          Next         = "Architecture"
        }]
        Default = "DiscoveryRevision"
      }

      DiscoveryRevision = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"              = "start_phase"
            "project_id.$"        = "$.project_id"
            "phase"               = "DISCOVERY"
            "task_token.$"        = "$$.Task.Token"
            "customer_feedback.$" = "$.approval.feedback"
          }
        }
        ResultPath = "$.discovery_result"
        Next       = "DiscoveryPMReview"
      }

      # =====================================================================
      # ARCHITECTURE
      # =====================================================================
      Architecture = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"            = "start_phase"
            "project_id.$"      = "$.project_id"
            "phase"             = "ARCHITECTURE"
            "task_token.$"      = "$$.Task.Token"
            "customer_feedback" = ""
          }
        }
        ResultPath = "$.architecture_result"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 10
          MaxAttempts     = 1
          BackoffRate     = 2.0
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "HandleError"
        }]
        Next = "ArchitecturePMReview"
      }

      ArchitecturePMReview = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.pm_review.arn
          Payload = {
            "project_id.$" = "$.project_id"
            "phase"        = "ARCHITECTURE"
          }
        }
        ResultPath     = "$.pm_review"
        ResultSelector = { "review_passed.$" = "$.Payload.review_passed" }
        Next           = "ArchitectureApproval"
      }

      ArchitectureApproval = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"       = "store_approval_token"
            "project_id.$" = "$.project_id"
            "phase"        = "ARCHITECTURE"
            "task_token.$" = "$$.Task.Token"
          }
        }
        ResultPath = "$.approval"
        Next       = "ArchitectureDecision"
      }

      ArchitectureDecision = {
        Type = "Choice"
        Choices = [{
          Variable     = "$.approval.decision"
          StringEquals = "APPROVED"
          Next         = "POC"
        }]
        Default = "ArchitectureRevision"
      }

      ArchitectureRevision = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"              = "start_phase"
            "project_id.$"        = "$.project_id"
            "phase"               = "ARCHITECTURE"
            "task_token.$"        = "$$.Task.Token"
            "customer_feedback.$" = "$.approval.feedback"
          }
        }
        ResultPath = "$.architecture_result"
        Next       = "ArchitecturePMReview"
      }

      # =====================================================================
      # POC
      # =====================================================================
      POC = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"            = "start_phase"
            "project_id.$"      = "$.project_id"
            "phase"             = "POC"
            "task_token.$"      = "$$.Task.Token"
            "customer_feedback" = ""
          }
        }
        ResultPath = "$.poc_result"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 10
          MaxAttempts     = 1
          BackoffRate     = 2.0
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "HandleError"
        }]
        Next = "POCPMReview"
      }

      POCPMReview = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.pm_review.arn
          Payload = {
            "project_id.$" = "$.project_id"
            "phase"        = "POC"
          }
        }
        ResultPath     = "$.pm_review"
        ResultSelector = { "review_passed.$" = "$.Payload.review_passed" }
        Next           = "POCApproval"
      }

      POCApproval = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"       = "store_approval_token"
            "project_id.$" = "$.project_id"
            "phase"        = "POC"
            "task_token.$" = "$$.Task.Token"
          }
        }
        ResultPath = "$.approval"
        Next       = "POCDecision"
      }

      POCDecision = {
        Type = "Choice"
        Choices = [{
          Variable     = "$.approval.decision"
          StringEquals = "APPROVED"
          Next         = "Production"
        }]
        Default = "POCRevision"
      }

      POCRevision = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"              = "start_phase"
            "project_id.$"        = "$.project_id"
            "phase"               = "POC"
            "task_token.$"        = "$$.Task.Token"
            "customer_feedback.$" = "$.approval.feedback"
          }
        }
        ResultPath = "$.poc_result"
        Next       = "POCPMReview"
      }

      # =====================================================================
      # PRODUCTION
      # =====================================================================
      Production = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"            = "start_phase"
            "project_id.$"      = "$.project_id"
            "phase"             = "PRODUCTION"
            "task_token.$"      = "$$.Task.Token"
            "customer_feedback" = ""
          }
        }
        ResultPath = "$.production_result"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 10
          MaxAttempts     = 1
          BackoffRate     = 2.0
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "HandleError"
        }]
        Next = "ProductionPMReview"
      }

      ProductionPMReview = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.pm_review.arn
          Payload = {
            "project_id.$" = "$.project_id"
            "phase"        = "PRODUCTION"
          }
        }
        ResultPath     = "$.pm_review"
        ResultSelector = { "review_passed.$" = "$.Payload.review_passed" }
        Next           = "ProductionApproval"
      }

      ProductionApproval = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"       = "store_approval_token"
            "project_id.$" = "$.project_id"
            "phase"        = "PRODUCTION"
            "task_token.$" = "$$.Task.Token"
          }
        }
        ResultPath = "$.approval"
        Next       = "ProductionDecision"
      }

      ProductionDecision = {
        Type = "Choice"
        Choices = [{
          Variable     = "$.approval.decision"
          StringEquals = "APPROVED"
          Next         = "Handoff"
        }]
        Default = "ProductionRevision"
      }

      ProductionRevision = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"              = "start_phase"
            "project_id.$"        = "$.project_id"
            "phase"               = "PRODUCTION"
            "task_token.$"        = "$$.Task.Token"
            "customer_feedback.$" = "$.approval.feedback"
          }
        }
        ResultPath = "$.production_result"
        Next       = "ProductionPMReview"
      }

      # =====================================================================
      # HANDOFF
      # =====================================================================
      Handoff = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"            = "start_phase"
            "project_id.$"      = "$.project_id"
            "phase"             = "HANDOFF"
            "task_token.$"      = "$$.Task.Token"
            "customer_feedback" = ""
          }
        }
        ResultPath = "$.handoff_result"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 10
          MaxAttempts     = 1
          BackoffRate     = 2.0
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "HandleError"
        }]
        Next = "HandoffPMReview"
      }

      HandoffPMReview = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.pm_review.arn
          Payload = {
            "project_id.$" = "$.project_id"
            "phase"        = "HANDOFF"
          }
        }
        ResultPath     = "$.pm_review"
        ResultSelector = { "review_passed.$" = "$.Payload.review_passed" }
        Next           = "HandoffApproval"
      }

      HandoffApproval = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"       = "store_approval_token"
            "project_id.$" = "$.project_id"
            "phase"        = "HANDOFF"
            "task_token.$" = "$$.Task.Token"
          }
        }
        ResultPath = "$.approval"
        Next       = "HandoffDecision"
      }

      HandoffDecision = {
        Type = "Choice"
        Choices = [{
          Variable     = "$.approval.decision"
          StringEquals = "APPROVED"
          Next         = "ProjectComplete"
        }]
        Default = "HandoffRevision"
      }

      HandoffRevision = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        Parameters = {
          FunctionName = aws_lambda_function.sfn_handlers.arn
          Payload = {
            "action"              = "start_phase"
            "project_id.$"        = "$.project_id"
            "phase"               = "HANDOFF"
            "task_token.$"        = "$$.Task.Token"
            "customer_feedback.$" = "$.approval.feedback"
          }
        }
        ResultPath = "$.handoff_result"
        Next       = "HandoffPMReview"
      }

      # =====================================================================
      # TERMINAL STATES
      # =====================================================================
      ProjectComplete = {
        Type = "Succeed"
      }

      HandleError = {
        Type  = "Fail"
        Error = "PhaseOrchestrationError"
        Cause = "A phase failed after exhausting all retries. Check CloudWatch logs."
      }
    }
  })

  tags = { Name = "cloudcrew-orchestrator-${var.environment}" }
}
