# FortiGate-VM on AWS — Terraform Quick Deploy

Stand up a **FortiGate-VM (BYOL)** on AWS with Terraform in ~3 minutes. The FortiOS AMI is **resolved live from the Fortinet-owned AMI catalog** — no hardcoded AMI IDs — so it works in **any region** and always lands on the current GA build for the version + architecture you pick.

**Status:** ✅ Partner-ready

## What it deploys
- 1 VPC + public (WAN) and private (LAN) subnets + Internet Gateway
- 1 **FortiGate-VM (BYOL)**, dual-NIC (`port1` WAN + `port2` LAN), with an **Elastic IP** on the WAN
- Security group: admin GUI (`443`) + SSH (`22`) from **your IP only**, intra-VPC, all egress
- Minimal bootstrap: hostname, admin password, interfaces, default route, DNS

## Why the AMI is looked up, not hardcoded
There's no AMI ID to find or maintain. The `data "aws_ami"` block filters on:

| Filter | Value |
|---|---|
| **Owner** | `679593333241` (Fortinet) |
| **Name** | `FortiGate-VMARM64-AWS build* (7.6.7) GA-*` (arm64) or `FortiGate-VM64-AWS build* (7.6.7) GA-*` (x86_64) |
| **most_recent** | `true` |

> The literal `" build"` in the name filter is what **excludes the PAYG (`-AWSONDEMAND`) image** — so you always land on **BYOL**.

## Prerequisites
1. **Terraform ≥ 1.3** and AWS credentials configured (`aws configure`, an env profile, or SSO).
2. **Subscribe once (free) to the FortiGate-VM _BYOL_ Marketplace product** in your AWS account — otherwise `terraform apply` fails with `OptInRequired`. (AWS Marketplace → search "FortiGate VM" → the BYOL listing → *Subscribe*.)
3. A **FortiFlex or perpetual license** to apply after boot — BYOL means you bring the license.

## Deploy
```bash
cp terraform.tfvars.example terraform.tfvars   # set admin_password + admin_cidr (your /32)
terraform init
terraform apply                                 # ~3 min
```
Outputs give the **public IP**, the **`https://<ip>/` admin URL**, and the exact AMI that was resolved.

## After apply
1. Browse the admin URL, log in as `admin` with the password you set.
2. **License it:** *System → FortiGuard*, or CLI `execute vm-license <token>`.
3. Configure to taste (interfaces, policies, VPN, SD-WAN…).

## Tear down
```bash
terraform destroy
```

## Common variables
| Variable | Default | Notes |
|---|---|---|
| `fortios_version` | `7.6.7` | any FortiOS GA build |
| `architecture` | `arm64` | `arm64` (t4g, cheapest) or `x86_64` (t3/c5) — must match `instance_type` |
| `instance_type` | `t4g.medium` | **≥ 4 GiB recommended** — FortiOS 7.6.x on 2 GiB can hit memory conserve mode |
| `admin_cidr` | `0.0.0.0/0` | **set this to your `/32`** |
| `key_pair_name` | `""` | optional — FortiGate login is the admin password |

## Notes
- The AMI ID is **region-specific**; because it's a live lookup you never touch it — set `aws_region`/`architecture`/`fortios_version` and Terraform finds the right BYOL image in your account.
- Secrets stay out of git: `terraform.tfvars` and state are `.gitignore`d; only `terraform.tfvars.example` is committed.

## ⚠️ Disclaimer
**Not an official Fortinet product.** Provided AS-IS for lab/PoC use — test before production. Neither the author nor Fortinet is liable for any outcome of using this tool.
