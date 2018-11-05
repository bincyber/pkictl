from helper import capture_stdout
from helper import ROOT_MANIFEST_YAML, PKI_MANIFEST_YAML
from pkictl import utils
from distutils.util import strtobool
from unittest.mock import patch, MagicMock
import io
import os
import sys
import tempfile
import unittest


class TestUtils(unittest.TestCase):
    def setUp(self):
        for i in ['VAULT_ADDR', 'VAULT_SKIP_VERIFY', 'VAULT_TOKEN']:
            try:
                os.environ.pop(i)
            except KeyError:
                pass

    def test_output_message(self):
        m = "standard output message"

        with capture_stdout(utils.output_message, msg=m) as output:
            self.assertEqual(output.strip(), f"[*] pkictl - {m}")

    def test_exit_with_message(self):
        m = "test error message"
        with self.assertRaises(SystemExit) as e:
            utils.exit_with_message(m)
        self.assertEqual(e.exception.args[0], f"[-] pkictl - Error: {m}")

    def test_get_from_environment_vault_address(self):
        k = 'VAULT_ADDR'
        v = "https://localhost:8200"

        buffer = io.BytesIO(bytes(v, encoding='utf-8'))
        sys.stdin = io.TextIOWrapper(buffer)
        r = utils.get_from_environment(k)
        self.assertEqual(r, v)

        os.environ[k] = v
        r = utils.get_from_environment(k)
        self.assertEqual(r, v)

    def test_get_from_environment_vault_token(self):
        k = 'VAULT_TOKEN'
        v = "TEST"

        buffer = io.BytesIO(bytes(v, encoding='utf-8'))
        sys.stdin = io.TextIOWrapper(buffer)
        with patch('getpass.getpass', MagicMock(return_value=input("Vault Token: "))):
            r = utils.get_from_environment(k)
            self.assertEqual(r, v)

        os.environ[k] = v
        r = utils.get_from_environment(k)
        self.assertEqual(r, v)

    def test_get_from_environment_vault_skip_verify(self):
        k = 'VAULT_SKIP_VERIFY'
        v = 'False'
        os.environ[k] = v
        r = utils.get_from_environment(k)
        self.assertEqual(r, v)

        r = strtobool(utils.get_from_environment(k))
        self.assertEqual(r, False)

        os.environ.pop('VAULT_SKIP_VERIFY')
        r = utils.get_from_environment(k)
        self.assertEqual(r, 'False')

    def test_get_manifest_files(self):
        with tempfile.TemporaryDirectory() as d:
            with tempfile.NamedTemporaryFile(dir=d, suffix='.yaml'), tempfile.NamedTemporaryFile(dir=d, suffix='.yml'):
                r = utils.get_manifest_files(directory=d)
                self.assertEqual(len(r), 2)
                for filename in r:
                    self.assertTrue(filename.endswith('.yml') or filename.endswith('.yaml'))

    def test_read_manifest_file(self):
        d = utils.read_manifest_file(ROOT_MANIFEST_YAML)
        self.assertIsInstance(d, list)

    def test_read_manifest_file_nonexistant(self):
        with self.assertRaises(SystemExit) as e:
            utils.read_manifest_file(path='/manifest.yaml')
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: manifest file does not exist")

    def test_read_manifest_file_invalid_yaml(self):
        t = tempfile.NamedTemporaryFile()
        t.write(b"---\nx: y:\n")
        t.seek(0)

        with self.assertRaises(SystemExit) as e:
            utils.read_manifest_file(path=t.name)
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: failed to parse manifest file, invalid YAML")

    def test_read_manifest_file_permission_denied(self):
        with self.assertRaises(SystemExit) as e:
            utils.read_manifest_file(path='/etc/shadow')
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: failed to read manifest file, permission denied")

    def test_get_validated_manifests(self):
        d = utils.read_manifest_file(PKI_MANIFEST_YAML)

        roots, intermediates, kv_backends = utils.get_validated_manifests(d)

        self.assertIsInstance(roots, list)
        self.assertEqual(len(roots), 2)
        self.assertIsInstance(intermediates, list)
        self.assertEqual(len(intermediates), 3)
        self.assertIsInstance(kv_backends, list)

    def test_write_vault_master_keys(self):
        with tempfile.NamedTemporaryFile() as t:
            m = ["aaa", "bbb", "ccc"]
            self.assertFalse(utils.write_vault_master_keys(m, t.name))

            with open(t.name, 'r') as f:
                self.assertIn("Unseal Key 1: aaa\n", f.readlines())

    def test_write_vault_master_keys_debug(self):
        with tempfile.NamedTemporaryFile() as t:
            m = ["1", "2", "3", "4", "5"]

            with capture_stdout(utils.write_vault_master_keys, master_keys=m, file=t.name, debug=True) as output:
                self.assertEqual(output.strip(), f"[*] pkictl - Successfully wrote the Vault master keys to {t.name}")

    def test_write_vault_master_keys_failed(self):
        with self.assertRaises(SystemExit) as e:
            utils.write_vault_master_keys(file='/etc/vault/vault.log')
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to write the Vault master keys to /etc/vault/vault.log")

    def test_write_vault_root_token(self):
        with tempfile.NamedTemporaryFile() as t:
            self.assertFalse(utils.write_vault_root_token("testoken", t.name))

    def test_write_vault_root_token_failed(self):
        with self.assertRaises(SystemExit) as e:
            utils.write_vault_root_token(file='/etc/vault/vault-token')
        self.assertEqual(e.exception.args[0], "[-] pkictl - Error: Failed to write the Vault root token to /etc/vault/vault-token")

    def test_write_vault_root_token_debug(self):
        with tempfile.NamedTemporaryFile() as t:
            with capture_stdout(utils.write_vault_root_token, root_token="testoken", file=t.name, debug=True) as output:
                self.assertEqual(output.strip(), f"[*] pkictl - Successfully wrote the Vault root token to {t.name}")

    def test_sort_intermediate_certificate_authorities(self):
        intermediates = [
            {
                'kind': 'IntermediateCA',
                'name': 'blah-ca',
                'issuer': 'bar-ca'
            },
            {
                'kind': 'IntermediateCA',
                'name': 'foo-ca',
                'issuer': 'root-ca'
            },
            {
                'kind': 'IntermediateCA',
                'name': 'bar-ca',
                'issuer': 'foo-ca'
            },
            {
                'kind': 'IntermediateCA',
                'name': 'kungfoo-ca',
                'issuer': 'root-ca'
            }
        ]

        expected = [
            {
                'kind': 'IntermediateCA',
                'name': 'kungfoo-ca',
                'issuer': 'root-ca'
            },
            {
                'kind': 'IntermediateCA',
                'name': 'foo-ca',
                'issuer': 'root-ca'
            },
            {
                'kind': 'IntermediateCA',
                'name': 'bar-ca',
                'issuer': 'foo-ca'
            },
            {
                'kind': 'IntermediateCA',
                'name': 'blah-ca',
                'issuer': 'bar-ca'
            }
        ]

        results = utils.sort_intermediate_certificate_authorities(intermediates)
        self.assertEqual(expected, results)
