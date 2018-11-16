# Environment Variables

_pkictl_ supports a subset of the [environment variables](https://www.vaultproject.io/docs/commands/#environment-variables) that the Vault CLI does.

The following environment variables are supported:
* VAULT_ADDR
* VAULT_TOKEN
* VAULT_SKIP_VERIFY

If the `-u` flag or `VAULT_ADDR` is not specified, the address of the Vault server will be prompted for.

If `VAULT_TOKEN` is not specified, it will be prompted for. The token cannot be supplied any other way.
