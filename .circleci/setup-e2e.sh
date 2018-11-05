#!/bin/sh

set -ex

VAULT_VERSION="0.11.4"

apt-get update -qq
apt-get install -y --no-install-recommends unzip wget openssl ca-certificates

wget -q "https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_amd64.zip"

unzip "vault_${VAULT_VERSION}_linux_amd64.zip"

cp vault /usr/local/bin/vault

mkdir -p /etc/vault/ssl /var/lib/vault

openssl req -x509 -newkey rsa:2048 -nodes -keyout /etc/vault/ssl/server.key -out /etc/vault/ssl/server.crt -days 365 -subj '/CN=Vault Server/'

cp pkictl/tests/e2e/config.hcl /etc/vault/config.hcl

/usr/local/bin/vault server -config /etc/vault/config.hcl &
