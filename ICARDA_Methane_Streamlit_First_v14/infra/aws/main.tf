data "aws_caller_identity" "current" {}

locals {
  name = var.project_name
}

resource "aws_security_group" "alb" {
  name   = "${local.name}-alb"
  vpc_id = var.vpc_id
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "app" {
  name   = "${local.name}-app"
  vpc_id = var.vpc_id
  ingress {
    from_port       = 4180
    to_port         = 4180
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name   = "${local.name}-db"
  vpc_id = var.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecr_repository" "app" {
  name                 = "${local.name}-platform"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
}

resource "aws_s3_bucket" "data" {
  bucket = "${local.name}-${data.aws_caller_identity.current.account_id}-${var.aws_region}-data"
}
resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" } }
}
resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_db_subnet_group" "db" {
  name       = "${local.name}-db"
  subnet_ids = var.private_subnet_ids
}
resource "aws_db_instance" "postgres" {
  identifier              = "${local.name}-postgres"
  engine                  = "postgres"
  engine_version          = "16.4"
  instance_class          = "db.t4g.medium"
  allocated_storage      = 50
  max_allocated_storage  = 200
  storage_encrypted      = true
  db_name                = "methane_platform"
  username               = "methane_app"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.db.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = true
  backup_retention_period = 14
  deletion_protection    = true
  skip_final_snapshot    = false
}

resource "aws_ecs_cluster" "main" {
  name = "${local.name}-cluster"
}
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name}"
  retention_in_days = 90
}
resource "aws_lb" "app" {
  name               = "${local.name}-alb"
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.alb.id]
}
resource "aws_lb_target_group" "app" {
  name        = "${local.name}-tg"
  port        = 4180
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check {
    path                = "/ping"
    healthy_threshold   = 2
    unhealthy_threshold = 5
    interval            = 30
  }
}
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_secretsmanager_secret" "entra" { name = "${local.name}/entra-client-secret" }
resource "aws_secretsmanager_secret_version" "entra" {
  secret_id     = aws_secretsmanager_secret.entra.id
  secret_string = var.entra_client_secret
}
resource "aws_secretsmanager_secret" "cookie" { name = "${local.name}/oauth-cookie-secret" }
resource "aws_secretsmanager_secret_version" "cookie" {
  secret_id     = aws_secretsmanager_secret.cookie.id
  secret_string = var.oauth_cookie_secret
}

resource "aws_security_group" "redis" {
  name   = "${local.name}-redis"
  vpc_id = var.vpc_id
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name}-redis"
  subnet_ids = var.private_subnet_ids
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${local.name}-redis"
  description                = "Redis queue/cache for methane phenotype analysis"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = "cache.t4g.small"
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled           = true
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
}

resource "aws_ecs_service" "app" {
  name            = "${local.name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = var.ecs_task_definition_arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  enable_execute_command = false
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "oauth2-proxy"
    container_port   = 4180
  }
  depends_on = [aws_lb_listener.https]
}
