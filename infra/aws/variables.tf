variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

variable "project_name" {
  type    = string
  default = "icarda-methane"
}

variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "public_subnet_ids" { type = list(string) }
variable "entra_tenant_id" { type = string }
variable "entra_client_id" { type = string }
variable "allowed_email_domain" { type = string }
variable "db_password" {
  type = string
  sensitive = true
}
variable "oauth_cookie_secret" {
  type = string
  sensitive = true
}
variable "entra_client_secret" {
  type = string
  sensitive = true
}
variable "acm_certificate_arn" { type = string }
variable "ecs_task_definition_arn" { type = string }
variable "desired_count" {
  type    = number
  default = 2
}
