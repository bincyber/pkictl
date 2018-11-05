# Schemas

_pkictl_ is driven using a YAML file wherein Root CAs, Intermediate CAs, and Key/Value engines are specified. Multiple documents can be in a single YAML file. _pkictl_ also supports reading multiple YAML files from a directory.

The [voluptuous](https://github.com/alecthomas/voluptuous) Python library is used to validate the schemas for each manifest. Schemas for Root CAs, Intermediate CAs, and Key/Value engines are defined in [schemas.py](https://github.com/bincyber/pkictl/blob/master/pkictl/schemas.py).

The `name` field of each manifest must be unique because it is [mounted](https://www.vaultproject.io/api/system/mounts.html#enable-secrets-engine) in Vault with the name set as the `path` parameter. It is recommended to prefix the names of CAs with `pki` and KV engines with `kv`. For example, an Intermediate CA should be named `pki/intermediate-ca` and its KV engine should be named `kv/intermediate-ca`.


### PKI Engines

_pkictl_ supports provisioning both RSA and ECDSA-based Root and Intermediate CAs. `key_bits` must be set to a valid value depending on if `key_type` is `rsa` or `ec`:
* for RSA, `key_bits` should be `2048` or `4096`
* for ECDSA, `key_bits` should be `256` or `384`

CRL location and issuing certificates are automatically set when a CA is provisioned. CRL configuration can be set for Intermediate CAs.


#### Roles

[Roles](https://www.vaultproject.io/api/secret/pki/index.html#create-update-role) for Intermediate CAs can be defined in the manifest:

    roles:
    - name: server
      config:
        max_ttl: 8766h
        ttl: 8766h
        allow_subdomains: true
        allowed_domains:
        - demo.pkictl.com
        client_flag: false
        server_flag: true

Refer to the Vault documentation for which [paramters](https://www.vaultproject.io/api/secret/pki/index.html#parameters-8) can be defined in a role. _pkictl_ does not currently support all parameters.

Each role must have a unique name within the scope of its associated Intermediate CA. Roles are updated every time _pkictl_ is ran.


#### Policies

[Policies](https://www.vaultproject.io/docs/concepts/policies.html) for Intermediate CAs can be defined in the manifest using HCL:

    policies:
    - name: demo-intermediate-ca-server
      policy: |
        path "demo-intermediate-ca/issue/server" {
            capabilities = ["read", "update"]
        }

        path "demo-intermediate-ca/sign/server" {
            capabilities = ["read", "update"]
        }

Each policy must have a globally unique name. Policies are updated every time _pkictl_ is ran.


### Key/Value Engines

The [Key/Value secrets engine](https://www.vaultproject.io/docs/secrets/kv/index.html) is only used to store the private keys of Intermediate CAs that are configured for [export](https://www.vaultproject.io/api/secret/pki/index.html#type). When `catype: exported` is set for an Intermediate CA, Vault returns the private key and _pkictl_ stores it in the KV engine specified with `kv_backend` under the [:key](https://www.vaultproject.io/api/secret/kv/kv-v1.html#key) `private_key`. By storing it in a KV engine, it can later be accessed if needed. _pkictl_ supports storing the private keys of Intermediate CAs in a single KV engine or a distinct KV engine for each Intermediate CA.

Currently, only version 1 of the Key/Value engine is supported.
