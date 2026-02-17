---
paths:
  - "infra/**"
---

# Terraform Rules (CloudCrew Infrastructure)

This is CloudCrew's OWN infrastructure (DynamoDB, Step Functions, ECS, API Gateway, etc.).
This is NOT the customer project infrastructure — agents write customer IaC to the project repo.

- All resources in `infra/terraform/`
- Use variables for everything configurable — no hardcoded values
- Pin provider versions
- Tag all resources: `Project = "cloudcrew"`, `ManagedBy = "terraform"`
- Use remote state (S3 + DynamoDB locking) in production
- Every `.tf` file should have a clear purpose (one per AWS service)
- Run `terraform validate` and `terraform fmt` before committing
- No IAM policies with `*` actions — use least privilege
- No security groups with `0.0.0.0/0` ingress unless explicitly required and documented
