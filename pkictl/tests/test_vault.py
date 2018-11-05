from pkictl.vault import VaultClient
from helper import capture_stdout, create_test_http_server, serialize_json
from helper import get_test_root_ca, get_test_intermediate_ca, get_test_kv_engine
from requests.models import Response
from unittest.mock import MagicMock
from urllib.parse import urljoin
import os
import tempfile
import unittest


class TestVaultClient(unittest.TestCase):
    def setUp(self):
        self.baseurl              = "https://localhost:8200"
        self.vault_client         = VaultClient(baseurl=self.baseurl)
        self.test_response        = Response()
        self.vault_client.request = MagicMock(return_value=self.test_response)

    def test_vault_header(self):
        token = 'TEST'
        header = {'X-VAULT-TOKEN': token}
        self.vault_client.token = token
        self.assertEqual(self.vault_client.headers, header)

    def test_health_check(self):
        self.test_response._content = serialize_json({"initialized": True, "sealed": True})

        initialized, sealed = self.vault_client.healthcheck()

        self.assertEqual(initialized, True)
        self.assertEqual(sealed, True)

        self.test_response.status_code = 200
        with capture_stdout(self.vault_client.healthcheck) as output:
            self.assertEqual(output.strip(), "[*] pkictl - the Vault server has been initialized and is not sealed")

        self.test_response.status_code = 501
        with capture_stdout(self.vault_client.healthcheck) as output:
            self.assertEqual(output.strip(), "[*] pkictl - the Vault server has not been initialized")

        self.test_response.status_code = 503
        with capture_stdout(self.vault_client.healthcheck) as output:
            self.assertEqual(output.strip(), "[-] pkictl - Error: the Vault server is sealed")

    def test_initialize_server(self):
        self.test_response.status_code = 200
        self.test_response._content    = serialize_json({"root_token": "test", "keys_base64": ["a", "b", "c", "d", "e"]})

        with tempfile.NamedTemporaryFile() as lf, tempfile.NamedTemporaryFile() as tf:
            with capture_stdout(self.vault_client.initialize_server, log_file=lf.name, token_file=tf.name) as output:
                self.assertEqual(output.strip(), "[*] pkictl - Initialized the Vault server")
            self.assertEqual(len(self.vault_client.master_keys), 5)

        self.test_response.status_code = 401
        with capture_stdout(self.vault_client.initialize_server) as output:
            self.assertEqual(output.strip(), "[-] pkictl - Error: failed to initialize the Vault server")

        # fails to write master keys to file
        self.test_response.status_code = 200
        with tempfile.NamedTemporaryFile() as t, self.assertRaises(SystemExit):
            os.chmod(t.name, 0o400)
            self.vault_client.initialize_server(log_file=t.name)

        # fails to write root token to file
        self.test_response.status_code = 200
        with tempfile.NamedTemporaryFile() as t, self.assertRaises(SystemExit):
            os.chmod(t.name, 0o400)
            self.vault_client.initialize_server(token_file=t.name)

    def test_unseal_server(self):
        self.vault_client.master_keys = ["a", "b", "c", "d", "e"]
        self.test_response._content = serialize_json({"sealed": False, "t": 3, "n": 5, "version": "11.3.0"})

        self.test_response.status_code = 200
        with capture_stdout(self.vault_client.unseal_server) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Unsealed the Vault server")

        self.test_response.status_code = 400
        with self.assertRaises(SystemExit) as e:
            self.vault_client.unseal_server()
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: failed to unseal the Vault server")

    def test_mount_kv_engine(self):
        kvengine = get_test_kv_engine(self.baseurl)

        self.test_response.status_code = 204
        with capture_stdout(self.vault_client.mount_kv_engine, kvengine) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Mounted KV secrets engine: test-kv")

    def test_mount_kv_engine_exists(self):
        kvengine = get_test_kv_engine(self.baseurl)

        self.test_response.status_code = 400
        with capture_stdout(self.vault_client.mount_kv_engine, kvengine) as output:
            self.assertEqual(output.strip(), "[*] pkictl - KV secrets engine 'test-kv' already exists")

    def test_mount_kv_engine_fail(self):
        kvengine = get_test_kv_engine(self.baseurl)

        self.test_response.status_code = 500

        with self.assertRaises(SystemExit) as e:
            self.vault_client.mount_kv_engine(kvengine)
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to mount KV secrets engine: test-kv")

    def test_store_ca_pkey(self):
        ca = get_test_intermediate_ca(self.baseurl)
        ca.private_key = '-----BEGIN RSA PRIVATE KEY----'

        self.test_response.status_code = 204
        with capture_stdout(self.vault_client.store_ca_private_key, ca) as output:
            self.assertEqual(output.strip(), f"[*] pkictl - Stored private key for 'test-intermediate-ca' in KV engine: test-kv")

    def test_store_ca_pkey_fail(self):
        ca = get_test_intermediate_ca(self.baseurl)
        ca.private_key = '-----BEGIN RSA PRIVATE KEY----'

        self.test_response.status_code = 500
        with self.assertRaises(SystemExit) as e:
            self.vault_client.store_ca_private_key(ca)
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to store private key for 'test-intermediate-ca' in KV engine: test-kv")

    def test_mount_pki_engine(self):
        rootca = get_test_root_ca(self.baseurl)

        self.test_response.status_code = 204
        with capture_stdout(self.vault_client.mount_pki_engine, rootca) as output:
            self.assertEqual(output.strip(), f"[*] pkictl - Mounted PKI secrets engine: test-root-ca")

        self.test_response.status_code = 400
        with capture_stdout(self.vault_client.mount_pki_engine, rootca) as output:
            self.assertEqual(output.strip(), f"[*] pkictl - PKI secrets engine 'test-root-ca' already exists")

    def test_mount_pki_engine_fail(self):
        rootca = get_test_root_ca(self.baseurl)

        self.test_response.status_code = 500
        with self.assertRaises(SystemExit) as e:
            self.vault_client.mount_pki_engine(rootca)
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to mount PKI secrets engine: test-root-ca")

    def test_check_existing_ca(self):
        rootca = get_test_root_ca(self.baseurl)

        self.test_response.status_code = 200
        self.assertTrue(self.vault_client.check_existing_ca(rootca))

        with capture_stdout(self.vault_client.check_existing_ca, rootca) as output:
            self.assertEqual(output.strip(), f"[*] pkictl - CA 'test-root-ca' already exists")

        self.test_response.status_code = 400
        self.assertFalse(self.vault_client.check_existing_ca(rootca))

    def test_create_root_ca(self):
        rootca = get_test_root_ca(self.baseurl)

        self.test_response.status_code = 200
        self.test_response._content    = serialize_json({"data": {"certificate": "-----BEGIN CERTIFICATE-----"}})

        with capture_stdout(self.vault_client.create_root_ca, rootca) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Generated Root CA: test-root-ca")

        self.test_response._content = serialize_json({"data": None})
        with capture_stdout(self.vault_client.create_root_ca, rootca) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Root CA 'test-root-ca' has already been generated")

        self.test_response.status_code = 204
        with capture_stdout(self.vault_client.create_root_ca, rootca) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Root CA 'test-root-ca' has already been generated")

    def test_create_root_ca_fail(self):
        rootca = get_test_root_ca(self.baseurl)

        self.test_response.status_code = 400
        self.test_response._content    = serialize_json({"data": {"certificate": "-----BEGIN CERTIFICATE-----"}})

        with self.assertRaises(SystemExit) as e:
            self.vault_client.create_root_ca(rootca)
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to generate Root CA: test-root-ca")

    def test_configure_ca_urls(self):
        rootca = get_test_root_ca(self.baseurl)

        self.test_response.status_code = 204
        with capture_stdout(self.vault_client.configure_ca_urls, rootca) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Configured URLs for CA: test-root-ca")

    def test_configure_ca_urls_fail(self):
        rootca = get_test_root_ca(self.baseurl)

        self.test_response.status_code = 400
        with self.assertRaises(SystemExit) as e:
            self.vault_client.configure_ca_urls(rootca)
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to configure URLs for CA: test-root-ca")

    def test_set_crl_configuration(self):
        ca = get_test_intermediate_ca(self.baseurl)

        self.test_response.status_code = 204
        with capture_stdout(self.vault_client.set_crl_configuration, ca) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Set CRL configuration for CA: test-intermediate-ca")

    def test_set_crl_configuration_fail(self):
        ca = get_test_intermediate_ca(self.baseurl)

        self.test_response.status_code = 400
        with self.assertRaises(SystemExit) as e:
            self.vault_client.set_crl_configuration(ca)
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to set CRL configuration for CA: test-intermediate-ca")

    def test_create_intermediate_ca(self):
        ca = get_test_intermediate_ca(self.baseurl)

        d = {"data": {"csr": "-----BEGIN CERTIFICATE REQUEST-----", 'private_key': '-----BEGIN RSA PRIVATE KEY----'}}

        self.test_response.status_code = 200
        self.test_response._content    = serialize_json(d)

        with capture_stdout(self.vault_client.create_intermediate_ca, ca) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Created intermediate CA: test-intermediate-ca")
        self.assertIsInstance(ca.csr, str)

    def test_create_intermediate_ca_fail(self):
        ca = get_test_intermediate_ca(self.baseurl)

        d = {"data": {"csr": "-----BEGIN CERTIFICATE REQUEST-----", 'private_key': '-----BEGIN RSA PRIVATE KEY----'}}

        self.test_response._content    = serialize_json(d)
        self.test_response.status_code = 400

        with self.assertRaises(SystemExit) as e:
            self.vault_client.create_intermediate_ca(ca)
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to generate intermediate CA: test-intermediate-ca")

    def test_sign_intermediate_ca(self):
        ca = get_test_intermediate_ca(self.baseurl)

        ca.csr = "-----BEGIN CERTIFICATE REQUEST-----"

        self.test_response.status_code = 200
        self.test_response._content    = serialize_json({"data": {"certificate": "-----BEGIN CERTIFICATE-----", "issuing_ca": "-----BEGIN CERTIFICATE-----"}})

        with capture_stdout(self.vault_client.sign_intermediate_ca, ca) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Signed intermediate CA 'test-intermediate-ca' with issuing CA: test-root-ca")
        self.assertIsInstance(ca.cert, str)

    def test_sign_intermediate_ca_fail(self):
        ca = get_test_intermediate_ca(self.baseurl)

        ca.csr = "-----BEGIN CERTIFICATE REQUEST-----"

        self.test_response.status_code = 500
        self.test_response._content    = serialize_json({"data": {"certificate": "-----BEGIN CERTIFICATE-----"}})

        with self.assertRaises(SystemExit) as e:
            self.vault_client.sign_intermediate_ca(ca)
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to sign intermediate CA 'test-intermediate-ca' with issuing CA: test-root-ca")

    def test_set_intermediate_ca(self):
        ca = get_test_intermediate_ca(self.baseurl)
        ca.cert = "-----BEGIN CERTIFICATE-----"

        self.test_response.status_code = 204
        with capture_stdout(self.vault_client.set_intermediate_ca, ca) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Set signed certificate for intermediate CA: test-intermediate-ca")

    def test_set_intermediate_ca_fail(self):
        ca = get_test_intermediate_ca(self.baseurl)
        ca.cert = "-----BEGIN CERTIFICATE-----"

        self.test_response.status_code = 500
        with self.assertRaises(SystemExit) as e:
            self.vault_client.set_intermediate_ca(ca)
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to set signed certificate for intermediate CA: test-intermediate-ca")

    def test_configure_ca_roles(self):
        ca = get_test_intermediate_ca(self.baseurl)

        # test a single role
        self.test_response.status_code = 204
        with capture_stdout(self.vault_client.configure_ca_roles, ca) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Configured role 'server' for intermediate CA: test-intermediate-ca")

    def test_configure_ca_roles_multiple(self):
        ca = get_test_intermediate_ca(self.baseurl)

        ca.dict['spec']['roles'].append({
            'name': 'client',
            'config': {
                'max_ttl': '26298h',
                'client_flag': True,
                'server_flag': False,
                'allow_any_name': True
            }
        })

        self.test_response.status_code = 204
        with capture_stdout(self.vault_client.configure_ca_roles, ca) as output:
            output = output.split('\n')
            self.assertEqual(output[0].strip(), "[*] pkictl - Configured role 'server' for intermediate CA: test-intermediate-ca")
            self.assertEqual(output[1].strip(), "[*] pkictl - Configured role 'client' for intermediate CA: test-intermediate-ca")

    def test_configure_ca_roles_fail(self):
        ca = get_test_intermediate_ca(self.baseurl)

        self.test_response.status_code = 500
        with self.assertRaises(SystemExit) as e:
            self.vault_client.configure_ca_roles(ca)
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to configure role 'server' for intermediate CA: test-intermediate-ca")

    def test_configure_ca_policies(self):
        ca = get_test_intermediate_ca(self.baseurl)

        self.test_response.status_code = 204
        with capture_stdout(self.vault_client.configure_ca_policies, ca) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Configured policy 'intermediate-ca-server-policy' for intermediate CA: test-intermediate-ca")

    def test_configure_ca_policies_fail(self):
        ca = get_test_intermediate_ca(self.baseurl)

        self.test_response.status_code = 500
        with self.assertRaises(SystemExit) as e:
            self.vault_client.configure_ca_policies(ca)
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to configure policy 'intermediate-ca-server-policy' for intermediate CA: test-intermediate-ca")

    # TO-DO
    # def test_configure_ca_policies_multiple(self):
    #     ca = get_test_intermediate_ca(self.baseurl)


class TestVaultClientRequests(unittest.TestCase):
    def setUp(self):
        self.baseurl      = "http://localhost:8222"
        self.vault_client = VaultClient(baseurl=self.baseurl)

        self.server = create_test_http_server()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_request_200(self):
        URL = urljoin(self.baseurl, '/')

        response = self.vault_client.request(method='GET', url=URL)
        self.assertIsInstance(response, Response)

    def test_request_debugging(self):
        self.vault_client.debugging = True

        URL = urljoin(self.baseurl, '/')

        with capture_stdout(self.vault_client.request, method='GET', url=URL) as output:
            self.assertEqual(output.strip(), "[*] pkictl - Request method: GET, Request URL: http://localhost:8222/, Response status code: 200, Response body:")

    def test_request_timeout(self):
        with self.assertRaises(SystemExit) as e:
            self.vault_client.request(method='GET', url="https://localhost:8200")

        self.assertIn("[-] pkictl - Error: Failed to contact the Vault server:", e.exception.args[0])

    def test_request_403(self):
        URL = urljoin(self.baseurl, '/403')

        with self.assertRaises(SystemExit) as e:
            self.vault_client.request(method='GET', url=URL)

        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to authenticate to the Vault server: invalid token")

    def test_request_404(self):
        URL = urljoin(self.baseurl, '/404')

        with self.assertRaises(SystemExit) as e:
            self.vault_client.request(method='GET', url=URL)

        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to process request: invalid path")
