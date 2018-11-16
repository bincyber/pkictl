from helper import ROOT_MANIFEST_YAML, INTERMEDIATE_MANIFEST_YAML, KV_MANIFEST_YAML
from pkictl import schemas
import unittest
import voluptuous
import yaml


class TestSchemas(unittest.TestCase):
    def test_root_schema_valid(self):

        test_data = {
            'kind': 'RootCA',
            'metadata': {
                'name': 'test-root-ca',
                'description': 'Test Root CA'
            },
            'spec': {
                'key_type': 'rsa',
                'key_bits': 2048,
                'ttl': '1000h',
                'subject': {
                    'common_name': 'Test Root CA'
                }
            }
        }

        self.assertIsInstance(schemas.RootCASchema(test_data), dict)

    def test_root_schema_invalid(self):

        test_data = {
            'kind': 'RootCA',
            'metadata': {
                'name': 'test-root-ca',
                'description': 'Test Root CA'
            },
            'spec': {
                'key_type': 'rsa',
                'key_bits': 4096,
            }
        }

        with self.assertRaises(voluptuous.MultipleInvalid):
            self.assertIsInstance(schemas.RootCASchema(test_data), dict)

    def test_intermediate_schema_valid(self):

        test_data = {
            'kind': 'IntermediateCA',
            'metadata': {
                'name': 'test-intermediate-ca-1',
                'description': 'Test Intermediate CA 1',
                'issuer': 'test-root-ca'
            },
            'spec': {
                'type': 'internal',
                'key_type': 'rsa',
                'key_bits': 4096,
                'subject': {
                    'common_name': 'Test Intermediate CA 1'
                },
                'crl': {
                    'expiry': '48h'
                },
                'roles': [{
                    'name': 'server',
                    'config': {
                        'max_ttl': '1000h',
                        'server_flag': True,
                        'client_flag': False,
                        'allow_subdomains': True,
                        'enforce_hostnames': True,
                        'allowed_domains': [
                            'test.example.com',
                            'testing.example.com'
                        ]
                    }
                }]
            }
        }

        self.assertIsInstance(schemas.IntermediateCASchema(test_data), dict)

        test_data = {
            'kind': 'IntermediateCA',
            'metadata': {
                'name': 'test-intermediate-ca-2',
                'description': 'Test Intermediate CA 2',
                'issuer': 'test-root-ca'
            },
            'spec': {
                'type': 'exported',
                'key_type': 'ec',
                'key_bits': 384,
                'subject': {
                    'common_name': 'Test Intermediate CA 2'
                },
                'roles': [{
                    'name': 'server',
                    'config': {
                        'max_ttl': '1000h',
                        'server_flag': True,
                        'client_flag': False,
                        'allow_subdomains': True,
                        'enforce_hostnames': True,
                        'allowed_domains': [
                            'test.example.com',
                            'testing.example.com'
                        ]
                    }
                }],
                'policies': [{
                    'name': 'test-intermediate-ca-2-server-policy',
                    'policy': 'ICAgICAgcGF0aCAiaW50ZXJtZWRpYXRlLWNhL2lzc3VlL3NlcnZlciIgewogICAgICAgIGNhcGFiaWxpdGllcyA9IFsicmVhZCIsICJ1cGRhdGUiXQogICAgICB9Cg=='
                }]
            }
        }

        self.assertIsInstance(schemas.IntermediateCASchema(test_data), dict)

    def test_intermediate_schema_invalid(self):

        test_data = {
            'kind': 'IntermediateCA',
            'metadata': {
                'name': 'test-intermediate-ca',
                'description': 'Test Intermediate CA',
                'issuer': 'test-root-ca'
            },
            'spec': {
                'type': 'internal',
                'key_type': 'ec',
                'key_bits': 8192
            }
        }

        with self.assertRaises(voluptuous.MultipleInvalid):
            self.assertIsInstance(schemas.IntermediateCASchema(test_data), dict)

    def test_schema_from_file(self):
        with open(ROOT_MANIFEST_YAML) as f:
            test_data = yaml.load(f.read())
            self.assertIsInstance(schemas.RootCASchema(test_data), dict)

        with open(INTERMEDIATE_MANIFEST_YAML) as f:
            test_data = yaml.load(f.read())
            self.assertIsInstance(schemas.IntermediateCASchema(test_data), dict)

        with open(KV_MANIFEST_YAML) as f:
            test_data = yaml.load(f.read())
            self.assertIsInstance(schemas.KeyValueSchema(test_data), dict)

    def test_schema_from_multidoc_file(self):
        with open('pkictl/tests/manifests/pki.yaml') as f:
            documents = yaml.load_all(f.read())

            for document in documents:
                schema_type = document.get('kind', None)

                if schema_type == 'RootCA':
                    self.assertIsInstance(schemas.RootCASchema(document), dict)
                elif schema_type == 'IntermediateCA':
                    self.assertIsInstance(schemas.IntermediateCASchema(document), dict)
                elif schema_type == 'KV':
                    self.assertIsInstance(schemas.KeyValueSchema(document), dict)
                else:
                    raise Exception("invalid schema type in YAML file")

    def test_kvengine_schema_valid(self):

        test_data = {
            'kind': 'KV',
            'metadata': {
                'name': 'test-kv-engine',
                'description': 'Test KV engine'
            },
            'spec': {
                'config': {
                    'default_lease_ttl': '100h'
                },
                'options': {
                    'version': 1
                }
            }
        }

        self.assertIsInstance(schemas.KeyValueSchema(test_data), dict)

    def test_kvengine_schema_invalid(self):

        test_data = {
            'kind': 'KV',
            'metadata': {
                'name': 'test-kv-engine',
                'description': 'Test KV engine'
            }
        }

        with self.assertRaises(voluptuous.MultipleInvalid):
            self.assertIsInstance(schemas.KeyValueSchema(test_data), dict)
