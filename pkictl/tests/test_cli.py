from pkictl.cli import cli
import argparse
import unittest


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.parser  = cli()
        self.baseurl = 'https://localhost:8200'

    def test_cli(self):
        t = self.parser.parse_args([])
        r = argparse.Namespace(debugging=False, subcommand=None)
        self.assertEqual(r, t)

    def test_init_subcommand(self):
        subcommand = 'init'

        t = self.parser.parse_args([subcommand, '--tls-skip-verify', '-u', self.baseurl])
        r = argparse.Namespace(baseurl=self.baseurl, debugging=False, subcommand=subcommand, tls_skip_verify=True)

        self.assertEqual(r, t)

    def test_apply_subcommand(self):
        subcommand = 'apply'

        t = self.parser.parse_args([subcommand, '-u', self.baseurl, '-f', 'test.yaml'])
        r = argparse.Namespace(baseurl=self.baseurl, debugging=False, subcommand=subcommand, tls_skip_verify=None, file='test.yaml')

        self.assertEqual(r, t)
