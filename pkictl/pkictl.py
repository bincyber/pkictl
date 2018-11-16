from .models import RootCA, IntermediateCA, KeyValueEngine
from .vault import VaultClient
from .cli import cli
from . import schemas, utils
from distutils.util import strtobool
import os.path
import requests
import sys


def main():
    parser = cli()
    args = parser.parse_args()

    if args.subcommand is None:
        parser.print_help()
        sys.exit()

    if args.baseurl is None:
        args.baseurl = utils.get_from_environment('VAULT_ADDR')

    if args.tls_skip_verify is None:
        args.tls_skip_verify = strtobool(utils.get_from_environment('VAULT_SKIP_VERIFY'))

    verify_ssl = True
    if args.tls_skip_verify:
        verify_ssl = False
        requests.packages.urllib3.disable_warnings()

    if args.subcommand == 'init':
        vault_client = VaultClient(baseurl=args.baseurl, verify_ssl=verify_ssl)

        initialized, sealed = vault_client.healthcheck()

        if not initialized:
            vault_client.initialize_server()

        if sealed:
            vault_client.unseal_server()

    elif args.subcommand == 'apply':
        # authentication token is required to talk to Vault
        vault_token = utils.get_from_environment('VAULT_TOKEN')

        vault_client = VaultClient(baseurl=args.baseurl, token=vault_token, debugging=args.debugging, verify_ssl=verify_ssl)

        path = os.path.abspath(os.path.expanduser(args.file))

        manifest_files = []
        documents      = []

        if os.path.isdir(path):
            manifest_files.extend(utils.get_manifest_files(path))
        else:
            manifest_files.append(path)

        for filepath in manifest_files:
            documents.extend(utils.read_manifest_file(filepath))

        _, sealed = vault_client.healthcheck()
        if sealed:
            sys.exit(1)

        roots, intermediates, kv_engines = utils.get_validated_manifests(documents)

        # mount KV engines
        for kve in kv_engines:
            kvengine = KeyValueEngine(args.baseurl, kve)
            vault_client.mount_kv_engine(kvengine)

        # create the Root CAs
        for ca in roots:
            manifest = schemas.RootCASchema(ca)
            root_ca  = RootCA(args.baseurl, manifest)

            vault_client.mount_pki_engine(root_ca)
            vault_client.create_root_ca(root_ca)
            if not vault_client.check_existing_ca(root_ca, quiet=True):
                vault_client.configure_ca_urls(root_ca)

        intermediates = utils.sort_intermediate_certificate_authorities(intermediates)

        # create the Intermediate CAs
        for ca in intermediates:
            manifest        = schemas.IntermediateCASchema(ca)
            intermediate_ca = IntermediateCA(args.baseurl, manifest)

            vault_client.mount_pki_engine(intermediate_ca)

            if not vault_client.check_existing_ca(intermediate_ca):
                vault_client.create_intermediate_ca(intermediate_ca)
                vault_client.sign_intermediate_ca(intermediate_ca)
                vault_client.set_intermediate_ca(intermediate_ca)
                vault_client.configure_ca_urls(intermediate_ca)
                vault_client.set_crl_configuration(intermediate_ca)

                if intermediate_ca.catype == 'exported':
                    vault_client.store_ca_private_key(intermediate_ca)

            vault_client.configure_ca_roles(intermediate_ca)
            vault_client.configure_ca_policies(intermediate_ca)
