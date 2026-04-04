# Minimal VPC — 2 public subnets across 2 AZs, no NAT Gateway.
# Worker nodes get public IPs so they can pull from ECR via the internet.
# S3 traffic routes through the free Gateway Endpoint (no data transfer cost).

resource "aws_vpc" "farsite" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, { Name = "${local.project}-vpc" })
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.farsite.id
  cidr_block              = cidrsubnet("10.0.0.0/16", 8, count.index)  # 10.0.0.0/24, 10.0.1.0/24
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true  # nodes get public IPs — required without NAT Gateway

  tags = merge(local.common_tags, {
    Name                                        = "${local.project}-public-${count.index + 1}"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/elb"                    = "1"
  })
}

resource "aws_internet_gateway" "farsite" {
  vpc_id = aws_vpc.farsite.id
  tags   = merge(local.common_tags, { Name = "${local.project}-igw" })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.farsite.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.farsite.id
  }

  tags = merge(local.common_tags, { Name = "${local.project}-public-rt" })
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Free S3 Gateway Endpoint — S3 traffic stays inside AWS, zero data transfer cost.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.farsite.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.public.id]

  tags = merge(local.common_tags, { Name = "${local.project}-s3-endpoint" })
}

