# VPC, public subnets, security groups.
# Dev uses public subnets only — NO NAT Gateways (~$32/month savings per gateway).
# ECS Fargate tasks run in public subnets with auto-assign public IP.

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "cloudcrew-${var.environment}" }
}

# --- Public Subnets (2 AZs) ---

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "cloudcrew-public-${count.index}-${var.environment}" }
}

# --- Internet Gateway ---

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "cloudcrew-igw-${var.environment}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "cloudcrew-public-rt-${var.environment}" }
}

resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# --- Security Group for ECS Tasks ---

resource "aws_security_group" "ecs_tasks" {
  name_prefix = "cloudcrew-ecs-tasks-"
  description = "Security group for ECS Fargate phase runner tasks"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "cloudcrew-ecs-tasks-${var.environment}" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_egress_rule" "ecs_https" {
  security_group_id = aws_security_group.ecs_tasks.id
  description       = "HTTPS to AWS services"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}
