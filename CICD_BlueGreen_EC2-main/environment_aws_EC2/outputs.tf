output "Server_Public_IPs" {
  value = {
    for idx, instance in concat(aws_instance.ubuntu_instance, aws_instance.RHEL8_instance) :
    instance.tags.Name => aws_eip.eip[idx].public_ip
  }
}
