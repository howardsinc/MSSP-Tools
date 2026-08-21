output "public_ip" {
  description = "FortiGate public IP (Elastic IP on the WAN interface)."
  value       = aws_eip.wan.public_ip
}

output "admin_url" {
  description = "FortiGate admin GUI URL. Default user 'admin' with the password you set."
  value       = "https://${aws_eip.wan.public_ip}/"
}

output "private_ips" {
  description = "Per-interface private IPs."
  value = {
    wan = aws_network_interface.wan.private_ip
    lan = aws_network_interface.lan.private_ip
  }
}

output "resolved_ami" {
  description = "The FortiOS AMI the live lookup resolved to (proves the version/arch lookup worked)."
  value       = { id = data.aws_ami.fortios.id, name = data.aws_ami.fortios.name }
}
