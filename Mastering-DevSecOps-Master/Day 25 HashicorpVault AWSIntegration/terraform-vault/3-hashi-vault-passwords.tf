resource "vault_mount" "java-app-dev" {
  path        = "java-app-dev"
  type        = "kv"
  options     = { version = "1" }
  description = "KV Version 1 secret engine mount"
}

resource "vault_kv_secret" "linux-machine-1" {
  path = "${vault_mount.java-app-dev.path}/linux-machine-1"
  data_json = jsonencode(
    {
      linux-machine-1 = random_password.linux-machine-passwords.0.result
    }
  )
}

resource "vault_kv_secret" "linux-machine-2" {
  path = "${vault_mount.java-app-dev.path}/linux-machine-2"
  data_json = jsonencode(
    {
      linux-machine-2 = random_password.linux-machine-passwords.1.result
    }
  )
}

resource "vault_kv_secret" "linux-machine-3" {
  path = "${vault_mount.java-app-dev.path}/linux-machine-3"
  data_json = jsonencode(
    {
      linux-machine-3 = random_password.linux-machine-passwords.2.result
    }
  )
}