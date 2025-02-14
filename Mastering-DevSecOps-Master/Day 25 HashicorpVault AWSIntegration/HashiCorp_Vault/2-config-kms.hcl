disable_cache = true
disable_mlock = true
ui            = true
listener "tcp" {
  address                  = "0.0.0.0:8200"
  tls_disable              = 0
  tls_cert_file            = "/etc/letsencrypt/live/cloudvishwakarma.in/fullchain.pem"
  tls_key_file             = "/etc/letsencrypt/live/cloudvishwakarma.in/privkey.pem"
  tls_disable_client_certs = "true"

}
storage "s3" {
  bucket = "workspacesbucket01"
}

seal "awskms" {
  region     = "us-east-1"
  kms_key_id = "KMSID here"
  endpoint   = "kms.us-east-1.amazonaws.com"
}

api_addr                = "https://kmsvault.cloudvishwakarma.in:8200"
max_lease_ttl           = "10h"
default_lease_ttl       = "10h"
cluster_name            = "vault"
raw_storage_endpoint    = true
disable_sealwrap        = true
disable_printable_check = true


