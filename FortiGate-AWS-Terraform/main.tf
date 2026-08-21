# =============================================================================
# FortiGate-VM (BYOL) on AWS — quick deploy.
# The AMI is resolved LIVE from the Fortinet-owned catalog — no hardcoded ID,
# works in any region and always lands on the current GA build.
#
# PREREQ: subscribe (once, free) to the FortiGate-VM BYOL Marketplace product
# in your account, or the launch fails with OptInRequired.
# =============================================================================

locals {
  # BYOL image name: "FortiGate-VMARM64-AWS build* (<ver>) GA-*" (arm64) or
  # "FortiGate-VM64-AWS build* (<ver>) GA-*" (x86_64). The literal " build" after
  # "-AWS" is what EXCLUDES the PAYG "-AWSONDEMAND" images — so you get BYOL.
  ami_name = var.architecture == "arm64" ? "FortiGate-VMARM64-AWS build* (${var.fortios_version}) GA-*" : "FortiGate-VM64-AWS build* (${var.fortios_version}) GA-*"
}

# Reproducible AMI lookup — owner 679593333241 = Fortinet.
data "aws_ami" "fortios" {
  most_recent = true
  owners      = ["679593333241"]

  filter {
    name   = "name"
    values = [local.ami_name]
  }
  filter {
    name   = "architecture"
    values = [var.architecture]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# =============================================================================
# Networking — VPC, WAN (public) + LAN (private) subnets, IGW
# =============================================================================
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(var.tags, { Name = "${var.hostname}-vpc" })
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.this.id
  tags   = merge(var.tags, { Name = "${var.hostname}-igw" })
}

resource "aws_subnet" "wan" {
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.wan_subnet_cidr
  availability_zone = var.availability_zone
  tags              = merge(var.tags, { Name = "${var.hostname}-wan" })
}

resource "aws_subnet" "lan" {
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.lan_subnet_cidr
  availability_zone = var.availability_zone
  tags              = merge(var.tags, { Name = "${var.hostname}-lan" })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = merge(var.tags, { Name = "${var.hostname}-public-rt" })
}

resource "aws_route_table_association" "wan" {
  subnet_id      = aws_subnet.wan.id
  route_table_id = aws_route_table.public.id
}

# =============================================================================
# Security group — admin GUI + SSH from your IP, intra-VPC, all egress
# =============================================================================
resource "aws_security_group" "fgt" {
  name_prefix = "${var.hostname}-"
  description = "FortiGate admin access"
  vpc_id      = aws_vpc.this.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
    description = "HTTPS admin GUI"
  }
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
    description = "SSH admin"
  }
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
    description = "Intra-VPC"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = merge(var.tags, { Name = "${var.hostname}-sg" })
}

# =============================================================================
# Interfaces (port1 WAN + port2 LAN), Elastic IP, instance
# =============================================================================
resource "aws_network_interface" "wan" {
  subnet_id         = aws_subnet.wan.id
  security_groups   = [aws_security_group.fgt.id]
  source_dest_check = false
  private_ips       = [cidrhost(var.wan_subnet_cidr, 10)]
  tags              = merge(var.tags, { Name = "${var.hostname}-wan-nic" })
}

resource "aws_network_interface" "lan" {
  subnet_id         = aws_subnet.lan.id
  security_groups   = [aws_security_group.fgt.id]
  source_dest_check = false
  private_ips       = [cidrhost(var.lan_subnet_cidr, 10)]
  tags              = merge(var.tags, { Name = "${var.hostname}-lan-nic" })
}

resource "aws_eip" "wan" {
  domain = "vpc"
  tags   = merge(var.tags, { Name = "${var.hostname}-eip" })
}

resource "aws_eip_association" "wan" {
  allocation_id        = aws_eip.wan.id
  network_interface_id = aws_network_interface.wan.id
}

resource "aws_instance" "fgt" {
  ami           = data.aws_ami.fortios.id
  instance_type = var.instance_type
  key_name      = var.key_pair_name != "" ? var.key_pair_name : null

  network_interface {
    network_interface_id = aws_network_interface.wan.id
    device_index         = 0
  }
  network_interface {
    network_interface_id = aws_network_interface.lan.id
    device_index         = 1
  }

  user_data = templatefile("${path.module}/bootstrap_fgt.tftpl", {
    hostname       = var.hostname
    admin_password = var.admin_password
    wan_ip         = cidrhost(var.wan_subnet_cidr, 10)
    wan_mask       = cidrnetmask(var.wan_subnet_cidr)
    wan_gw         = cidrhost(var.wan_subnet_cidr, 1)
    lan_ip         = cidrhost(var.lan_subnet_cidr, 10)
    lan_mask       = cidrnetmask(var.lan_subnet_cidr)
  })

  tags = merge(var.tags, { Name = var.hostname })

  lifecycle {
    # Bootstrap only runs at first boot; don't stop/start a live FGT on edits.
    ignore_changes = [user_data]
  }
}
