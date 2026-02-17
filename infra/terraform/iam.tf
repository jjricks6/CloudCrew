# IAM roles and policies.
# - ECS task execution role (pull ECR, write CloudWatch logs)
# - ECS task role (Bedrock invoke, DynamoDB [cloudcrew-projects + cloudcrew-metrics],
#     S3 [project artifacts + cloudcrew-patterns], Step Functions, AgentCore Memory)
# - Lambda execution roles (per function, including Finalize Metrics Lambda
#     which needs cloudcrew-metrics DynamoDB write + Bedrock KB re-sync)
# - Step Functions execution role
