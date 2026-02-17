---
paths:
  - "infra/**"
---

# Terraform Rules (CloudCrew Infrastructure)

This is CloudCrew's OWN infrastructure (DynamoDB, Step Functions, ECS, API Gateway, etc.).
This is NOT the customer project infrastructure — agents write customer IaC to the project repo.

## File Organization

```
infra/
├── bootstrap/         # One-time: S3 state bucket + DynamoDB lock table (local state)
├── terraform/         # Main stack: all CloudCrew resources (remote state via bootstrap)
│   ├── backend.tf     # S3 backend config
│   ├── providers.tf   # AWS provider + default tags
│   ├── variables.tf   # Shared variables
│   ├── budget.tf      # AWS Budget alarm
│   ├── networking.tf  # VPC, subnets (public only in dev)
│   ├── iam.tf         # Roles and policies
│   ├── dynamodb.tf    # Task ledger, approval tokens
│   ├── step_functions.tf
│   ├── ecs.tf         # Fargate cluster + task defs
│   ├── ecr.tf         # Container registry
│   ├── lambda.tf      # PM review, approval API, chat
│   ├── api_gateway.tf # REST + WebSocket
│   ├── cognito.tf     # Customer auth
│   ├── s3.tf          # SOW uploads, KB data, dashboard hosting
│   └── outputs.tf
└── docker/
    └── Dockerfile     # ECS phase runner image
```

## Conventions

- Use variables for everything configurable — no hardcoded values
- Pin provider versions (`~> 5.0`, not `>= 5.0`)
- Tag all resources: `Project = "cloudcrew"`, `Environment`, `ManagedBy = "terraform"` (set via provider default_tags)
- One `.tf` file per AWS service
- Run `terraform fmt` and `terraform validate` before committing
- Use `terraform.tfvars` for personal config (gitignored). Commit `example.tfvars` as template.

## Security

- No IAM policies with `*` actions — use least privilege
- No security groups with `0.0.0.0/0` ingress unless explicitly required and documented
- Encrypt all data at rest (S3 SSE, DynamoDB encryption, EBS encryption)
- No secrets in `.tf` files — use variables or AWS Secrets Manager

## Cost Controls

- **No NAT Gateways in dev** — use public subnets (~$32/month savings per gateway)
- **DynamoDB on-demand** — `PAY_PER_REQUEST` billing, never provisioned capacity in dev
- **No ECS Services** — only Fargate Tasks launched on-demand by Step Functions
- **ECR lifecycle policy** — keep last 5 images, expire untagged after 1 day
- **Budget alarm** — configured in `budget.tf`, alerts at 50% forecast and 80% actual
- **Tag everything** — enables filtering in AWS Cost Explorer by `Project = cloudcrew`

## Deployment Workflow

- **Manual only**: `make tf-apply` and `make tf-destroy`. NEVER automated apply.
- **CI validates only**: `terraform fmt -check` + `terraform validate` + Checkov. No plan, no apply.
- **Tear down after testing**: Run `make tf-destroy` after each milestone test session.
- **Bootstrap is permanent**: The state bucket and lock table stay running (~$0.02/month). Everything else gets destroyed.

## NEVER Rules (Terraform-specific)

- NEVER use `terraform apply -auto-approve` in any script or CI pipeline
- NEVER create NAT Gateways in dev environment
- NEVER use provisioned DynamoDB capacity in dev environment
- NEVER create always-on ECS Services — use Tasks launched by Step Functions
- NEVER hardcode AWS account IDs, ARNs, or secrets in `.tf` files
- NEVER commit `.terraform/`, `*.tfstate`, `*.tfplan`, or `.terraform.lock.hcl`
- NEVER commit `*.tfvars` (except `example.tfvars`)
