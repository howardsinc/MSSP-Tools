# ---------- AWS placement ----------
variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "availability_zone" {
  description = "AZ for the subnets."
  type        = string
  default     = "us-east-1a"
}

# ---------- FortiOS image (reproducible lookup — NO hardcoded AMI) ----------
variable "fortios_version" {
  description = "FortiOS GA version to deploy. Resolved live from the Fortinet-owned AMI catalog."
  type        = string
  default     = "7.6.7"
}

variable "architecture" {
  description = "CPU arch: 'arm64' (t4g/c7g, cheapest) or 'x86_64' (t3/c5). Must match instance_type."
  type        = string
  default     = "arm64"
  validation {
    condition     = contains(["arm64", "x86_64"], var.architecture)
    error_message = "architecture must be 'arm64' or 'x86_64'."
  }
}

variable "instance_type" {
  description = "EC2 type. Use >= 4 GiB (t4g.medium arm64 / t3.medium x86_64) — FortiOS 7.6.x on 2 GiB can hit memory conserve mode."
  type        = string
  default     = "t4g.medium"
}

# ---------- Instance ----------
variable "hostname" {
  description = "FortiGate hostname (also used as the resource name prefix)."
  type        = string
  default     = "fortigate-vm"
}

variable "admin_password" {
  description = "FortiGate admin password (min 8 chars)."
  type        = string
  sensitive   = true
}

variable "admin_cidr" {
  description = "CIDR allowed to reach the admin GUI (443) + SSH (22). Set to YOUR public IP/32 (`curl ifconfig.me`) — don't leave 0.0.0.0/0."
  type        = string
  default     = "0.0.0.0/0"
}

variable "key_pair_name" {
  description = "OPTIONAL existing EC2 key pair. FortiGate admin login is the password, so this is not required."
  type        = string
  default     = ""
}

# ---------- Networking ----------
variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "wan_subnet_cidr" {
  type    = string
  default = "10.0.1.0/24"
}

variable "lan_subnet_cidr" {
  type    = string
  default = "10.0.2.0/24"
}

variable "tags" {
  type    = map(string)
  default = { Project = "fortigate-aws-terraform", ManagedBy = "terraform" }
}
