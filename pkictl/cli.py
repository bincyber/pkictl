import argparse


def custom_formatter(prog):
    return argparse.HelpFormatter(prog, max_help_position=59, width=125)


def cli():
    parser = argparse.ArgumentParser(
        description     = "declaratively configure PKI secrets in Hashicorp Vault",
        formatter_class = custom_formatter
    )

    parser.add_argument('-d', '--debug', dest='debugging',
        action='store_true', default=False, help='enable debug output')
    parser.add_argument('-V', '--version', action='version', version='Vault-PKI 0.1')

    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand', metavar='')

    init = subparsers.add_parser(
        'init',
        help="Initializes the Hashicorp Vault server",
        formatter_class=custom_formatter
    )

    init.add_argument('-u', '--url', dest='baseurl', type=str, metavar='URL',
        action='store', required=False, help='the URL of the Vault server')
    init.add_argument('--tls-skip-verify', nargs='?', dest='tls_skip_verify',
        const=True, default=None, help="disable verification of the Vault server's SSL certificate")

    apply = subparsers.add_parser(
        'apply',
        help="Creates PKI secrets from a YAML file",
        formatter_class=custom_formatter
    )

    apply.add_argument('-u', '--url', dest='baseurl', type=str, metavar='URL',
        action='store', required=False, help='the URL of the Vault server')
    apply.add_argument('-f', '--file', dest='file', type=str,
        action='store', required=True, help='the path to the configuration manifest(s)')
    apply.add_argument('--tls-skip-verify', nargs='?', dest='tls_skip_verify',
        const=True, default=None, help="disable verification of the Vault server's SSL certificate")

    return parser
