# Provision PKI for Kubernetes

[kubeadm](https://kubernetes.io/docs/setup/independent/high-availability/) can be used to deploy a HA Kubernetes cluster with multiple master nodes. However, this requires bootstrapping the first Kubernetes master node with `kubeadm init` so that the TLS certificates are created and then the certificates and private keys need to be manually copied to the other master nodes. See the documentation on the PKI certificates that kubeadm creates: https://kubernetes.io/docs/setup/certificates/. Julia Evans also has a fantastic blog post on the different Certificate Authorities that exist in a Kubernetes cluster: https://jvns.ca/blog/2017/08/05/how-kubernetes-certificates-work/.

_pkictl_ can be used to simplify the process of provisioning the PKI for Kubernetes and remove the need to manually copy certificates between the control plane nodes.

## Provision the Certificate Authorities

This example is for provisioning a control plane which uses external etcd. Define the Certificate Authorities to provision in the YAML manifest file:

    ---
    kind: KV
    name: kv/kube-ca
    description: exported PKI secrets for the Kubernetes CA
    spec:
      options:
        version: 1
    ---
    kind: KV
    name: kv/kube-fp-ca
    description: exported PKI secrets for the Kubernetes Front Proxy CA
    spec:
      options:
        version: 1
    ---
    kind: RootCA
    name: pki/kube-root-ca
    description: Kubernetes Root CA
    spec:
      key_type: rsa
      key_bits: 4096
      ttl: '87600h'
      exclude_cn_from_sans: true
      subject:
        common_name: Kubernetes Root Certificate Authority
    ---
    kind: IntermediateCA
    name: pki/etcd-ca
    description: Intermediate CA for etcd
    issuer: pki/root-ca
    spec:
      type: internal
      key_type: rsa
      key_bits: 2048
      ttl: 43800h
      subject:
        common_name: etcd Certificate Authority
      roles:
      - name: peer
        config:
          max_ttl: 26298h
          ttl: 17532h
          allow_subdomains: true
          allowed_domains:
            - etcd.example.com
          client_flag: true
          server_flag: true
      - name: server
        config:
          max_ttl: 26298h
          ttl: 17532h
          allow_subdomains: true
          allowed_domains:
            - etcd.example.com
          client_flag: false
          server_flag: true
      - name: client
        config:
          max_ttl: 26298h
          ttl: 17532h
          allow_any_name: true
          client_flag: true
          server_flag: false
      policies:
      - name: etcd-ca-server-policy
        policy: |
          path "pki/etcd-ca/issue/peer" {
            capabilities = ["read", "update"]
          }
          path "pki/etcd-ca/sign/peer" {
            capabilities = ["read", "update"]
          }
          path "pki/etcd-ca/issue/server" {
            capabilities = ["read", "update"]
          }
          path "pki/etcd-ca/sign/server" {
            capabilities = ["read", "update"]
          }
      - name: etcd-ca-client-policy
        policy: |
          path "pki/etcd-ca/issue/client" {
            capabilities = ["read", "update"]
          }
          path "pki/etcd-ca/sign/client" {
            capabilities = ["read", "update"]
          }
    ---
    kind: IntermediateCA
    name: pki/kube-ca
    description: Kubernetes CA
    issuer: pki/kube-root-ca
    kv_backend: kv/kube-ca
    spec:
      type: exported
      key_type: rsa
      key_bits: 4096
      ttl: 43800h
      subject:
        common_name: Kubernetes Certificate Authority
      policies:
      - name: kv-kube-ca-policy
        policy: |
          path "kv/kube-ca" {
            capabilities = ["read"]
          }
    ---
    kind: IntermediateCA
    name: pki/kube-fp-ca
    description: Kubernetes Front Proxy CA
    issuer: pki/kube-root-ca
    kv_backend: kv/kube-fp-ca
    spec:
      type: exported
      key_type: rsa
      key_bits: 4096
      ttl: 43800h
      subject:
        common_name: Kubernetes Front Proxy Certificate Authority
      roles:
      - name: client
        config:
          max_ttl: 26298h
          ttl: 17532h
          allow_any_name: true
          client_flag: true
          server_flag: false
      policies:
      - name: kube-fp-ca-client-policy
        policy: |
          path "pki/kube-fp-ca/issue/client" {
            capabilities = ["read", "update"]
          }
          path "pki/kube-fp-ca/sign/client" {
            capabilities = ["read", "update"]
          }
      - name: kv-kube-fp-ca-policy
        policy: |
          path "kv/kube-fp-ca" {
            capabilities = ["read"]
          }

The above will create:
- a Root CA for the Kubernetes cluster with a TTL of 10 years
- an Intermediate CA for etcd with a TTL of 5 years
  - a Role named `peer` to generate/sign TLS certificates for the etcd [peer server](https://coreos.com/etcd/docs/latest/v2/configuration.html#--peer-cert-file) for any subdomains on etcd.example.com
  - a Role named `server` to generate/sign TLS certificates for the etcd [client server](https://coreos.com/etcd/docs/latest/v2/configuration.html#--cert-file) for any subdomains on etcd.example.com
  - a Role named `client` to generate or sign TLS certificates for etcd clients since [--client-cert-auth](https://coreos.com/etcd/docs/latest/v2/configuration.html#--client-cert-auth) is enabled
  - a Policy mapped to the `peer` and `server` Roles and a Policy mapped to the `client` Role

- an Intermediate CA for the Kubernetes API server with a TTL of 5 years
  - this CA issues client certificates used to permit kubelet, controller manager, and scheduler to authenticate to the Kubernetes API server
  - the private key for this intermediate CA is exported and stored in the KV engine kv/kube-ca so that it can be retrieved by the Kubernetes master nodes
  - a Policy permitting the CA private key to be retrieved from the KV engine
  - while a Role and Policy can be defined for this CA, it's simpler to place the CA cert and private key on the master nodes and leave the generation of the actual TLS certificates to kubeadm

- an Intermediate CA for the Kubernetes [Aggregation layer](https://kubernetes.io/docs/tasks/access-kubernetes-api/configure-aggregation-layer/) with a TTL of 5 years
  - the private key for this intermediate CA is exported and stored in the KV engine kv/kube-fp-ca so that it can be retrieved by the Kubernetes master nodes
  - a Role named `client` to generate or sign TLS client certificates for the front-proxy
  - a Policy mapped to the `client` Role

## Programmatically retrieve certificates

After the CAs are provisioned in Vault, certificates can be programmatically retrieved by the Kubernetes master nodes. This example will show how this can be done using Ansible. We will assume that the external etcd cluster is already operational.

Obtain a Vault token for each policy created in the previous step:

    # token to retrieve etcd client certificates
    $ vault token create -policy=etcd-ca-client-policy -ttl=1h

    # token to retrieve Kubernetes CA cert and private key
    $ vault token create -policy=kv-kube-ca-policy -ttl=1h

    # token to retrieve Kubernetes front-proxy CA certificate and private key
    $ vault token create -policy=kv-kube-fp-ca-policy -ttl=1h

    # token to retrieve Kubernetes front-proxy client certificate
    $ vault token create -policy=kube-fp-ca-client-policy -ttl=1h


Ansible's [uri](https://docs.ansible.com/ansible/latest/modules/uri_module.html) module and [hashi_vault](https://docs.ansible.com/ansible/latest/plugins/lookup/hashi_vault.html) lookup plugin can be used to retrieve the certificates from the Vault server on the control plane nodes.

For example, to retrieve the certificate of the Kubernetes CA, the _uri_ module can be used to fetch it from Vault and the _copy_ module to save it to disk:

    - name: uri | retrieve the Kubernetes CA certificate
      uri:
        url: "https://localhost:8200/v1/pki/kube-ca/ca/pem"
        method: GET
        return_content: yes
        validate_certs: no
        status_code: 200
      register: kube_ca

    - name: uri | save the Kubernetes CA certificate
      copy:
        content: '{{ kube_ca.content }}'
        dest: "/etc/kubernetes/pki/ca.crt"
        owner: root
        mode: 0644

* retrieving a [CA certificate](https://www.vaultproject.io/api/secret/pki/index.html#read-ca-certificate) from Vault does not require authentication

To retrieve the private key of the Kubernetes CA from the KV engine in which it is stored, the _hashi_vault_ lookup plugin can be used with the _copy_ module:

    - name: copy | save the private key for the Kubernetes CA
      copy:
        content: "{{ lookup('hashi_vault', 'secret=kv/kube-ca/pki/kube-ca url=https://localhost:8200 validate_certs=False token=' ~ vault_token).private_key }}"
        dest: "/etc/kubernetes/pki/ca.key"
        mode: 0600

* `vault_token` is an Ansible variable (encrypted using [ansible-vault](https://docs.ansible.com/ansible/2.4/vault.html)) containing the Vault token with sufficient privileges to read the `kv/kube-ca` KV engine

A client certificate issued by the etcd CA can also be obtained using the _uri_ module:

    vars:
      kube_apiserver_etcd_client_cert:
        common_name: kube-apiserver

    tasks:
      - name: uri | obtain a client certificate issued by the etcd CA
        uri:
          url: "https://localhost:8200/v1/pki/etcd-ca/issue/client"
          method: POST
          body: "{{ kube_apiserver_etcd_client_cert | to_json }}"
          body_format: json
          return_content: yes
          validate_certs: no
          status_code: 200
          headers:
            X-VAULT-TOKEN: "{{ vault_token }}"
        register: etcd_client_cert

      - name: copy | save the client certificate
        copy:
          content: '{{ etcd_client_cert.json.data.certificate }}'
          dest: "/etc/kubernetes/pki/apiserver-etcd-client.crt"
          owner: root
          mode: 0644

      - name: copy | save the client private key
        copy:
          content: '{{ etcd_client_cert.json.data.private_key }}'
          dest: "/etc/kubernetes/pki/apiserver-etcd-client.key"
          owner: root
          mode: 0600
