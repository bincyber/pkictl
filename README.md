# pkictl

[![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)](#)
[![Version](https://img.shields.io/badge/version-0.1.2-green.svg)](#)
[![License](https://img.shields.io/badge/license-MPL-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.en.html)
[![Coverage Status](https://coveralls.io/repos/github/bincyber/pkictl/badge.svg?branch=master)](https://coveralls.io/github/bincyber/pkictl?branch=master)
[![CircleCI](https://circleci.com/gh/bincyber/pkictl.svg?style=svg)](https://circleci.com/gh/bincyber/pkictl)


_pkictl_ is a CLI tool for declaratively configuring and provisioning PKI secrets in HashiCorp Vault. Root and Intermediate Certificate Authorities (CAs) along with their associated roles and policies can be defined and created from a YAML file. It simplifies automating the provisioning of an internal PKI using Vault and strives to achieve idempotency.

_pkictl_ is inspired by [_kubectl_](https://kubernetes.io/docs/reference/kubectl/overview/).


## How It Works

_pkictl_ uses the Vault HTTP API to mount [PKI secrets engines](https://www.vaultproject.io/docs/secrets/pki/index.html) for Root and Intermediate CAs. Intermediate CAs can be signed by a Root CA or other Intermediate CAs. Roles and Policies can be defined in the YAML file for Intermediate CAs.

The [Key/Value secrets engine](https://www.vaultproject.io/docs/secrets/kv/index.html) is also used to store the private keys of Intermediate CAs that are configured for export (ie. `spec.type: exported`).


## Installation

_pkictl_ can be installed via pip:

	$ pip install pkictl


### Compatibility

_pkictl_ has been tested against versions 0.10.X and 0.11.X of Vault.

## Usage

    $ pkictl --help

    declaratively configure PKI secrets in Hashicorp Vault

    optional arguments:
    -h, --help     show this help message and exit
    -d, --debug    enable debug output
    -v, --version  show program's version number and exit

    subcommands:

        init         Initializes the Hashicorp Vault server
        apply        Creates PKI secrets from a YAML file


### Prerequisites

If you're unfamiliar with Vault's PKI secrets, read this guide: [Build Your Own Certificate Authority (CA)](https://learn.hashicorp.com/vault/secrets-management/sm-pki-engine)

_pkictl_ requires an unsealed Hashicorp Vault server and an authentication token with privileges to:
* mount PKI and KV secrets engines
* read and write PKI secrets
* write KV secrets


### Initializing the Vault server

Initialize a new Vault server and unseal it:

    $ pkictl init -u https://localhost:8200

The Vault server will be initialized with 5 key shares and a key threshold of 3.
* the root token is saved in `.vault-token`
* the master keys shares are saved in `vault.log`

Initializing and unsealing the Vault server this way is only provided as a convenience for development/testing and is highly discouraged.


### Declaratively provisioning PKI secrets

A YAML manifest file is used to define Root and Intermediate CAs, Key/Value engines, roles and policies.

Create a [manifest file](docs/examples/manifest.yaml):

    ---
    kind: RootCA
    name: demo-root-ca
    description: pkictl demo Root CA
    spec:
      key_type: ec
      key_bits: 384
      ttl: 17532h
      exclude_cn_from_sans: true
      subject:
        common_name: Demo Root CA
        organization: pkictl
        ou: README Demo
        country: US
        locality: San Francisco
        province: California
    ---
    kind: IntermediateCA
    name: demo-intermediate-ca
    description: pkictl demo Intermediate CA
    issuer: demo-root-ca
    kv_backend: demo-kv-engine
    spec:
      type: exported
      key_type: rsa
      key_bits: 4096
      ttl: 8766h
      subject:
        common_name: Demo Intermediate CA
        organization: pkictl
        ou: README Demo
        country: US
        locality: San Francisco
        province: California
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
      policies:
      - name: demo-intermediate-ca-pkey
        policy: |
          path "demo-kv-engine" {
            capabilities = ["list"]
          }
          path "demo-kv-engine/demo-intermediate-ca" {
            capabilities = ["read"]
          }
      - name: demo-intermediate-ca-server
        policy: |
          path "demo-intermediate-ca/issue/server" {
            capabilities = ["read", "update"]
          }
          path "demo-intermediate-ca/sign/server" {
            capabilities = ["read", "update"]
          }
    ---
    kind: KV
    name: demo-kv-engine
    description: pkictl demo KV v1 engine
    spec:
      options:
        version: 1

The above example will create:
- a ECDSA-based [Root](https://www.vaultproject.io/api/secret/pki/index.html#generate-root) CA with a TTL of 2 years
- an RSA-based [Intermediate](https://www.vaultproject.io/api/secret/pki/index.html#generate-intermediate) CA with a TTL of 1 year signed by the Root CA
- a [Role](https://www.vaultproject.io/api/secret/pki/index.html#create-update-role) named `server` permitting the Intermediate CA to generate or sign TLS server certificates for any subdomains on demo.pkictl.com
- a [Policy](https://www.vaultproject.io/docs/concepts/policies.html) mapped to the `server` role
- a [Key/Value](https://www.vaultproject.io/api/secret/kv/kv-v1.html) engine to store the exported private key of the Intermediate CA

Create PKI secrets from the YAML manifest file:

    $ pkictl apply -u https://localhost:8200 -f manifest.yaml

    [*] pkictl - the Vault server has been initialized and is not sealed
    [*] pkictl - Enabled KV backend: demo-kv-engine
    [*] pkictl - Enabled PKI backend: demo-root-ca
    [*] pkictl - Generated Root CA: demo-root-ca
    [*] pkictl - Enabled PKI backend: demo-intermediate-ca
    [*] pkictl - Created intermediate CA: demo-intermediate-ca
    [*] pkictl - Signed intermediate CA 'demo-intermediate-ca' with issuing CA: demo-root-ca
    [*] pkictl - Set signed certificate for intermediate CA: demo-intermediate-ca
    [*] pkictl - Configured URLs for CA: demo-intermediate-ca
    [*] pkictl - Set CRL configuration for CA: demo-intermediate-ca
    [*] pkictl - Stored private key for 'demo-intermediate-ca' in KV backend: demo-kv-engine
    [*] pkictl - Configured role 'server' for intermediate CA: demo-intermediate-ca
    [*] pkictl - Configured policy 'demo-intermediate-ca-server' for intermediate CA: demo-intermediate-ca
    [*] pkictl - Configured policy 'demo-intermediate-ca-pkey' for intermediate CA: demo-intermediate-ca

Obtain a Vault token:

    $ vault token create -policy=demo-intermediate-ca-server -ttl=1h

Use this token to obtain a TLS server certificate and private key for web.demo.pkictl.com from the Intermediate CA:

    $ vault write demo-intermediate-ca/issue/server common_name=web.demo.pkictl.com ttl=2160h

Alternatively, you can generate a certificate signing request (CSR) and private key locally and have the CSR signed by the Intermediate CA:

    $ openssl req -batch -nodes -sha256 -new -newkey rsa:2048 \
      -keyout web.demo.pkictl.com.key -out web.demo.pkictl.com.csr -subj '/CN=web.demo.pkictl.com/'

    $ vault write demo-intermediate-ca/sign/server csr=@web.demo.pkictl.com.csr ttl=2160h

Vault will return the signed TLS server certificate along with the full chain (the certificates for the Root and Intermediate CA).

Since `spec.type: exported`, the private key of this CA has been saved in the KV engine `demo-kv-engine`. A separate Vault token is required to retrieve it:

    $ vault token create -policy=demo-intermediate-ca-pkey -ttl=1m
    $ vault kv get -version=1 demo-kv-engine/demo-intermediate-ca

### Documentation

For documentation and additional examples, see the [docs](https://github.com/bincyber/pkictl/tree/master/docs) directory.

### Testing

[nose2](http://nose2.readthedocs.io/en/latest/) is used for testing. Tests are located in `pkictl/tests`.

To run the unit tests:

    $ make test

End to end tests requires Vault running locally. To build and run the Vault container:

    $ make build-vault-container
    $ make run-vault-container

Run the end-to-end tests:

    $ make e2e-test
