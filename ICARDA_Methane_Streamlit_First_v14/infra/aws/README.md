# AWS deployment starter (Terraform)

This starter provisions/references the core AWS boundary: private encrypted RDS PostgreSQL, versioned private S3 bucket, ECS cluster/service, ALB, ElastiCache Redis, ECR repository, security groups, CloudWatch log group and Secrets Manager entries.

## Prerequisites
- AWS account and approved region; confirm CGIAR/ICARDA data residency and security requirements.
- Existing VPC with private and public subnets across at least two AZs.
- ACM certificate for the public application domain.
- ECR image and ECS task execution/task roles.
- Microsoft Entra app registration and approved redirect URI.

## Important before applying
This Terraform is a starter, not a complete deployable stack. The ECS task definition must be rendered and registered separately; the task execution/task roles, database URL secret, API token secret, ECR image push, ALB DNS/Route 53, ACM validation, IAM policies, NAT/VPC endpoints, WAF, alarms and complete secret injection are not yet fully wired. RDS password and OIDC secrets should be supplied via a secure CI/CD secret mechanism, not committed to tfvars. Review RDS engine version availability and instance sizing in the selected region.

Render the dashboard task template with `python infra/aws/render_task_definition.py`. Supply the required environment variables from a secure deployment pipeline, then review the rendered JSON before registering it with ECS. The renderer does not create secrets; the referenced Secrets Manager ARNs must already exist.

Run `terraform fmt -recursive`, `terraform validate`, then `terraform plan` only after completing the missing resources and reviewing the plan with AWS/CGIAR IT. Do not apply this starter to a production account as-is.
