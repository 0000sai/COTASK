#Generating random password for Linux Machines
resource "random_password" "linux-machine-passwords" {
  count            = var.vm_count
  length           = 16
  special          = true
  override_special = "!@#$%^"
  min_upper        = 4
  min_lower        = 4
  min_special      = 4
  min_numeric      = 4
}