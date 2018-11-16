from . import schemas
from typing import List, Tuple, Optional
import getpass
import glob
import os
import sys
import yaml


def output_message(msg: str, err: bool = False):
    prefix = "[-]" if err else "[*]"
    message = [prefix, 'pkictl', '-', msg]
    if err:
        message.insert(3, "Error:")
    print(' '.join(message), flush=True)


def exit_with_message(msg: str):
    sys.exit(f"[-] pkictl - Error: {msg}")


def get_from_environment(name: str):
    value = os.getenv(name)
    if name == 'VAULT_ADDR' and value is None:
        return input("Vault URL: ")
    elif name == 'VAULT_TOKEN' and value is None:
        return getpass.getpass('Vault Token: ')
    elif name == 'VAULT_SKIP_VERIFY' and value is None:
        return 'False'
    return value


def get_manifest_files(directory: str) -> List[str]:
    """ returns a list of absolute paths to YAML manifest files within a directory """
    pattern  = '*.y[am]*l'  # match .yaml or .yml
    return glob.glob(f'{directory}/{pattern}')


def read_manifest_file(path: str) -> List[dict]:
    try:
        with open(path, 'r') as f:
            return list(yaml.load_all(f.read()))
    except FileNotFoundError:
        error_message = "manifest file does not exist"
    except yaml.YAMLError:
        error_message = "failed to parse manifest file, invalid YAML"
    except PermissionError:
        error_message = "failed to read manifest file, permission denied"
    except Exception as err:
        error_message = f"failed to read manifest file. Exception: {err}"
    return exit_with_message(error_message)


def get_validated_manifests(documents: List[dict]=[]) -> Tuple[List[dict], List[dict], List[dict]]:
    roots: List[dict]           = []
    intermediates: List[dict]   = []
    kv_engines: List[dict]     = []

    for i in documents:
        schema_type = i.get('kind')

        if schema_type == 'RootCA':
            roots.append(schemas.RootCASchema(i))

        elif schema_type == 'IntermediateCA':
            ca_name     = i['metadata']['name']
            ca_type     = i['spec'].get('type')
            kv_engine  = i['metadata'].get('kv_engine', None)

            if ca_type == 'exported' and kv_engine is None:
                exit_with_message(f"kv_engine not defined for exported intermediate CA: {ca_name}")

            intermediates.append(schemas.IntermediateCASchema(i))

        elif schema_type == 'KV':
            kv_engines.append(schemas.KeyValueSchema(i))

        else:
            exit_with_message("Unsupported schema defined in manifest file")
    return roots, intermediates, kv_engines


def write_vault_master_keys(master_keys: List[str]=[], file: str='vault.log', debug: bool=False) -> None:
    try:
        with open(file, 'w') as f:
            for i, v in enumerate(master_keys, 1):
                f.write(f"Unseal Key {i}: {v}\n")
    except Exception:
        exit_with_message(f"Failed to write the Vault master keys to {file}")
    else:
        os.chmod(file, 0o600)
        if debug:
            output_message(f"Successfully wrote the Vault master keys to {file}")


def write_vault_root_token(root_token: str=None, file: str='.vault-token', debug: bool=False) -> None:
    try:
        with open(file, 'w') as f:
            f.write(f"{root_token}\n")
    except Exception:
        exit_with_message(f"Failed to write the Vault root token to {file}")
    else:
        os.chmod(file, 0o600)
        if debug:
            output_message(f"Successfully wrote the Vault root token to {file}")


def get_issuer_index(array: List[dict], key: str, value: str) -> Optional[int]:
    for i, d in enumerate(array):
        if d['metadata'][key] == value:
            return i
    return None


def sort_intermediate_certificate_authorities(intermediates: List[dict]):
    sorted_intermediates: List[dict] = []
    for ca in intermediates:
        issuer = ca['metadata']['issuer']

        index = get_issuer_index(intermediates, key='name', value=issuer)
        if index is None:
            sorted_intermediates.insert(0, ca)
        else:
            sorted_intermediates.insert(index, ca)
    return sorted_intermediates
