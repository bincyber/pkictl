from helper import ROOT_MANIFEST_YAML, INTERMEDIATE_MANIFEST_YAML, KV_MANIFEST_YAML
from pkictl.models import RootCA, IntermediateCA, KeyValueEngine
import unittest
import yaml


class TestRootCA(unittest.TestCase):
    def setUp(self):
        self.baseurl = "https://localhost:8200"

    def test_root_ca(self):
        with open(ROOT_MANIFEST_YAML) as f:
            d = yaml.load(f.read())

        rootca = RootCA(self.baseurl, d)

        self.assertEqual(rootca.name, d['metadata']['name'])
        self.assertEqual(rootca.description, d['metadata']['description'])
        self.assertNotIn('subject', rootca.spec)
        self.assertIn('common_name', rootca.spec)
        self.assertEqual(rootca.ttl, d['spec']['ttl'])
        self.assertEqual(rootca.url, f'{self.baseurl}/v1/test-root-ca/root/generate/internal')
        self.assertEqual(rootca.config_url, f'{self.baseurl}/v1/test-root-ca/config/urls')


class TestIntermediateCA(unittest.TestCase):
    def setUp(self):
        self.baseurl = "https://localhost:8200"

    def test_intermediate_ca(self):
        with open(INTERMEDIATE_MANIFEST_YAML) as f:
            d = yaml.load(f.read())

        intermediate_ca = IntermediateCA(self.baseurl, d)

        self.assertEqual(intermediate_ca.name, d['metadata']['name'])
        self.assertEqual(intermediate_ca.description, d['metadata']['description'])
        self.assertEqual(intermediate_ca.issuer, d['metadata']['issuer'])
        self.assertNotIn('subject', intermediate_ca.spec)
        self.assertNotIn('policies', intermediate_ca.spec)
        self.assertNotIn('roles', intermediate_ca.spec)
        self.assertIn('common_name', intermediate_ca.spec)
        self.assertEqual(intermediate_ca.ttl, d['spec']['ttl'])
        self.assertEqual(intermediate_ca.issuer_sign_url, f'{self.baseurl}/v1/test-root-ca/root/sign-intermediate')
        self.assertEqual(intermediate_ca.set_signed_url, f'{self.baseurl}/v1/test-intermediate-ca/intermediate/set-signed')


class TestKeyValueEngine(unittest.TestCase):
    def setUp(self):
        self.baseurl = "https://localhost:8200"

    def test_keyvalue_engine(self):
        with open(KV_MANIFEST_YAML) as f:
            d = yaml.load(f.read())

        kv_engine = KeyValueEngine(self.baseurl, d)

        name = d['metadata']['name']

        self.assertEqual(kv_engine.name, name)
        self.assertEqual(kv_engine.url, f"{self.baseurl}/v1/sys/mounts/{name}")

        self.assertNotIn('kind', kv_engine.spec)
        self.assertNotIn('name', kv_engine.spec)
        self.assertIn('type', kv_engine.spec)
        self.assertIn('description', kv_engine.spec)
        self.assertIn('options', kv_engine.spec)
