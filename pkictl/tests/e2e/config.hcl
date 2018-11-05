backend "file" {
  path = "/var/lib/vault"
}

listener "tcp" {
  address = "0.0.0.0:8200"
  tls_cert_file = "/etc/vault/ssl/server.crt"
  tls_disable = 0
  tls_key_file = "/etc/vault/ssl/server.key"
  tls_min_version = "tls12"
}

disable_mlock = true
max_lease_ttl = "100000h"
ui = true
