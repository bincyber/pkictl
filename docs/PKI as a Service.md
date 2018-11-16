# PKI as a Service

Sébastien Braun of Hashicorp has an excellent guide to running PKI as a Service using Vault. You can read it here: https://yet.org/2018/10/vault-pki/

_pkictl_ can be used to ease and simplify the initial steps of configuring the PKI secrets in Vault.

Create the YAML manifest file:

	$ vim pki-as-a-service.yaml

    ---
    kind: RootCA
    metadata:
      name: root
      description: PKI-as-a-Service Root CA
    spec:
      key_type: rsa
      key_bits: 4096
      ttl: 87600h
      exclude_cn_from_sans: true
      subject:
        common_name: Root CA
    ---
    kind: IntermediateCA
    metadata:
      name: intermediate
      description: PKI-as-a-Service Intermediate CA
      issuer: root
    spec:
      type: internal
      key_type: rsa
      key_bits: 4096
      ttl: 43800h
      crl:
        expiry: 2m
      subject:
        common_name: pki-ca-int
      roles:
      - name: yet-dot-org
        config:
          max_ttl: 2m
          ttl: 2m
          allow_any_name: true
          generate_lease: true
          client_flag: false
          server_flag: true
      policies:
      - name: pki-int
        policy: |
          path "pki_int/issue/*" {
          capabilities = ["create", "update"]
          }

          path "pki_int/certs" {
          capabilities = ["list"]
          }

          path "pki_int/revoke" {
          capabilities = ["create", "update"]
          }

          path "pki_int/tidy" {
          capabilities = ["create", "update"]
          }

          path "pki/cert/ca" {
          capabilities = ["read"]
          }

          path "auth/token/renew" {
          capabilities = ["update"]
          }

          path "auth/token/renew-self" {
          capabilities = ["update"]
          }


Create the PKI secrets from the YAML manifest file:

    $ pkictl apply -u https://VAULT_IP:8200 -f pki-as-a-service.yaml

_pkictl_ will automatically create the Root and Intermediate CAs, configure the role and policy for the Intermediate CA, and set the duration for which the Intermediate CA's CRL should be marked valid.
