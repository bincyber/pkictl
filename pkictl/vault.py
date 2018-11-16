from . import utils
from urllib.parse import urljoin
import requests


class VaultClient:
    def __init__(self, baseurl=None, token=None, verify_ssl=True, debugging=False):
        self.baseurl     = baseurl
        self.token       = token
        self.verify_ssl  = verify_ssl
        self.debugging   = debugging
        self.timeout     = 80
        self.master_keys = []

    @property
    def headers(self):
        return {'X-VAULT-TOKEN': self.token}

    def request(self, method, url, headers=None, json=None):
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
        except requests.exceptions.RequestException as err:
            utils.exit_with_message(f"Failed to contact the Vault server: {err}")
        else:
            if self.debugging:
                msg = f"Request method: {method}, Request URL: {url}, Response status code: {response.status_code}, Response body: {response.text}"
                utils.output_message(msg)

            # See: https://www.vaultproject.io/api/index.html#http-status-codes
            if response.status_code == 403:
                utils.exit_with_message("Failed to authenticate to the Vault server: invalid token")
            elif response.status_code == 404:
                utils.exit_with_message("Failed to process request: invalid path")
            return response

    def healthcheck(self):
        """ checks if the Vault server has been initialized and is not sealed """
        URL = urljoin(self.baseurl, "v1/sys/health")

        response = self.request(method='GET', url=URL)
        body     = response.json()

        initialized = body['initialized']
        sealed      = body['sealed']

        if response.status_code == 200:
            utils.output_message("the Vault server has been initialized and is not sealed")
        elif response.status_code == 501:
            utils.output_message("the Vault server has not been initialized")
        elif response.status_code == 503:
            utils.output_message("the Vault server is sealed", err=True)
        return initialized, sealed

    def initialize_server(self, log_file='vault.log', token_file='.vault-token'):
        """" initializes the Vault server and writes master & root key to disk """
        URL = urljoin(self.baseurl, "v1/sys/init")

        params = {
            "secret_shares": 5,
            "secret_threshold": 3
        }

        response = self.request(method='PUT', url=URL, json=params)

        if response.status_code == 200:
            body = response.json()

            self.master_keys = body['keys_base64']
            self.token = body['root_token']

            utils.write_vault_master_keys(self.master_keys, log_file, self.debugging)
            utils.write_vault_root_token(self.token, token_file, self.debugging)

            utils.output_message("Initialized the Vault server")
        else:
            utils.output_message("failed to initialize the Vault server", err=True)

    def unseal_server(self):
        """" unseals the Vault server """
        URL = urljoin(self.baseurl, "v1/sys/unseal")

        for i in self.master_keys:
            response = self.request(method='PUT', url=URL, json={'key': i})

            if response.status_code == 200:
                body = response.json()

                if not body['sealed']:
                    utils.output_message("Unsealed the Vault server")
                    break
            else:
                utils.exit_with_message("failed to unseal the Vault server")

    def mount_kv_engine(self, kvengine):
        """ mounts a KV v1 secrets engine """
        response = self.request(method='POST', url=kvengine.url, headers=self.headers, json=kvengine.spec)

        if response.status_code == 204:
            utils.output_message(f"Mounted KV secrets engine: {kvengine.name}")
        elif response.status_code == 400:
            utils.output_message(f"KV secrets engine '{kvengine.name}' already exists")
        else:
            utils.exit_with_message(f"Failed to mount KV secrets engine: {kvengine.name}")

    def store_ca_private_key(self, ca):
        """ stores the private key for a CA in the specified KV engine """

        response = self.request(method='PUT', url=ca.kv_engine_url, headers=self.headers, json=ca.private_key)

        if response.status_code == 204:
            utils.output_message(f"Stored private key for '{ca.name}' in KV engine: {ca.kv_engine}")
        else:
            utils.exit_with_message(f"Failed to store private key for '{ca.name}' in KV engine: {ca.kv_engine}")

    def mount_pki_engine(self, ca):
        """ mounts a PKI secrets engine """
        URL = urljoin(self.baseurl, f"v1/sys/mounts/{ca.name}")

        response = self.request(method='POST', url=URL, headers=self.headers, json=ca.backend)

        if response.status_code == 204:
            utils.output_message(f"Mounted PKI secrets engine: {ca.name}")
        elif response.status_code == 400:
            utils.output_message(f"PKI secrets engine '{ca.name}' already exists")
        else:
            utils.exit_with_message(f"Failed to mount PKI secrets engine: {ca.name}")

    def check_existing_ca(self, ca, quiet=False):
        """ checks if a CA already exists """
        ca_exists = False

        URL = urljoin(self.baseurl, f"/v1/{ca.name}/ca/pem")

        response = self.request(method='GET', url=URL, headers=self.headers)

        if response.status_code == 200:
            ca_exists = True
            if not quiet:
                utils.output_message(f"CA '{ca.name}' already exists")
        return ca_exists

    def create_root_ca(self, ca):
        """ generates a Root CA """
        URL = urljoin(self.baseurl, f"/v1/{ca.name}/root/generate/internal")

        response = self.request(method='POST', url=URL, headers=self.headers, json=ca.spec)

        if response.status_code == 200:
            body = response.json()
            if body['data'] is not None:
                utils.output_message(f"Generated Root CA: {ca.name}")
            else:
                utils.output_message(f"Root CA '{ca.name}' has already been generated")
        elif response.status_code == 204:
            utils.output_message(f"Root CA '{ca.name}' has already been generated")
        else:
            utils.exit_with_message(f"Failed to generate Root CA: {ca.name}")

    def configure_ca_urls(self, ca):
        """ configures URLs for a CA """
        response = self.request(method='POST', url=ca.config_url, headers=self.headers, json=ca.ca_urls)

        if response.status_code == 204:
            utils.output_message(f"Configured URLs for CA: {ca.name}")
        else:
            utils.exit_with_message(f"Failed to configure URLs for CA: {ca.name}")

    def set_crl_configuration(self, ca):
        """ sets the duration for CRL validity """
        response = self.request(method='POST', url=ca.crl_config_url, headers=self.headers, json=ca.crl_config)

        if response.status_code == 204:
            utils.output_message(f"Set CRL configuration for CA: {ca.name}")
        else:
            utils.exit_with_message(f"Failed to set CRL configuration for CA: {ca.name}")

    def create_intermediate_ca(self, ca):
        """ generates an Intermediate CA """
        response = self.request(method='POST', url=ca.url, headers=self.headers, json=ca.spec)

        if response.status_code == 200:
            body = response.json()
            ca.csr = body['data']['csr']

            if ca.catype == 'exported':
                ca.private_key = body['data']['private_key']

            utils.output_message(f"Created intermediate CA: {ca.name}")
        else:
            utils.exit_with_message(f"Failed to generate intermediate CA: {ca.name}")

    def sign_intermediate_ca(self, ca):
        """ signs the certificate for an Intermediate CA with another CA """
        spec = ca.spec.copy()
        spec.update(csr=ca.csr)

        response = self.request(method='POST', url=ca.issuer_sign_url, headers=self.headers, json=spec)

        if response.status_code == 200:
            body        = response.json()
            certificate = body['data']['certificate']

            # there is no ca_chain for Root CAs
            try:
                ca_chain = '\n'.join(body['data'].get('ca_chain'))
            except TypeError:
                ca_chain = body['data']['issuing_ca']

            # include the full chain with the signed certificate
            ca.cert = f"{certificate}\n{ca_chain}"

            utils.output_message(f"Signed intermediate CA '{ca.name}' with issuing CA: {ca.issuer}")
        else:
            utils.exit_with_message(f"Failed to sign intermediate CA '{ca.name}' with issuing CA: {ca.issuer}")

    def set_intermediate_ca(self, ca):
        """ sets the signed certificate for an Intermediate CA """

        params = {'certificate': ca.cert}

        response = self.request(method='POST', url=ca.set_signed_url, headers=self.headers, json=params)

        if response.status_code == 204:
            utils.output_message(f"Set signed certificate for intermediate CA: {ca.name}")
        else:
            utils.exit_with_message(f"Failed to set signed certificate for intermediate CA: {ca.name}")

    def configure_ca_roles(self, ca):
        """ configures roles for an Intermediate CA """
        for role in ca.roles:
            name = role['name']
            config = role['config']

            URL = urljoin(self.baseurl, f"/v1/{ca.name}/roles/{name}")

            response = self.request(method='POST', url=URL, headers=self.headers, json=config)

            if response.status_code == 204:
                utils.output_message(f"Configured role '{name}' for intermediate CA: {ca.name}")
            else:
                utils.exit_with_message(f"Failed to configure role '{name}' for intermediate CA: {ca.name}")

    def configure_ca_policies(self, ca):
        for policy in ca.policies:
            name = policy['name']
            document = {'policy': policy['policy']}

            URL = urljoin(self.baseurl, f"/v1/sys/policies/acl/{name}")

            response = self.request(method='PUT', url=URL, headers=self.headers, json=document)

            if response.status_code == 204:
                utils.output_message(f"Configured policy '{name}' for intermediate CA: {ca.name}")
            else:
                utils.exit_with_message(f"Failed to configure policy '{name}' for intermediate CA: {ca.name}")
