from voluptuous import Schema, Required, Optional, All, Any, Range, Match, Coerce

MOUNT_PATH_REGEX = r'^(?![-\/])[a-z0-9-_\/]+(?<![-\/])$'

RootCASchema = Schema({
    Required('kind'): All('RootCA', msg="Must be 'RootCA'"),
    Required('metadata'): {
        Required('name'): Match(MOUNT_PATH_REGEX, msg="Must be lowercase alphanumberic string"),
        Required('description'): str
    },
    Required('spec'): {
        Required('key_type'): Any('rsa', 'ec', msg="Must be 'rsa' or 'ec'"),
        Required('key_bits'): Range(min=256, max=4096),
        Optional('ttl', default='87660h'): Match(r'\d+h'),
        Optional('exclude_cn_from_sans', default=True): bool,
        Required('subject'): {
            Required('common_name'): str,
            Optional('country'): Match(r'[A-Z]{2}'),
            Optional('locality'): str,
            Optional('province'): str,
            Optional('organization'): str,
            Optional('ou'): str
        }
    }
})

IntermediateCASchema = Schema({
    Required('kind'): All('IntermediateCA', msg="Must be 'IntermediateCA'"),
    Required('metadata'): {
        Required('name'): Match(MOUNT_PATH_REGEX, msg="Must be lowercase alphanumberic string"),
        Required('description'): str,
        Required('issuer'): Match(MOUNT_PATH_REGEX, msg="Must be lowercase alphanumberic string"),
        Optional('kv_engine'): Match(MOUNT_PATH_REGEX, msg="Must be lowercase alphanumberic string")
    },
    Required('spec'): {
        Required('type'): Any('internal', 'exported', msg="Must be 'internal' or 'exported'"),
        Required('key_type'): Any('rsa', 'ec', msg="Must be 'rsa' or 'ec'"),
        Required('key_bits'): Range(min=256, max=4096),
        Optional('ttl', default='87660h'): Match(r'\d+h'),
        Optional('exclude_cn_from_sans', default=True): bool,
        Optional('max_path_length', default=0): Range(min=-1, max=5),
        Optional('crl', default={}): {
            Optional('expiry', default='72h'): Match(r'\d+[hms]'),
            Optional('disable', default=False): bool
        },
        Required('subject'): {
            Required('common_name'): str,
            Optional('country'): Match(r'[A-Z]{2}'),
            Optional('locality'): str,
            Optional('province'): str,
            Optional('organization'): str,
            Optional('ou'): str,
        },
        Optional('roles', default=[]): [{
            Required('name'): Match(r'^[a-z0-9-_]+$', msg="Must be lowercase alphanumberic string"),
            Required('config'): {
                Required('max_ttl'): Match(r'\d+[hms]'),
                Optional('ttl'): Match(r'\d+[hms]'),
                Required('server_flag'): bool,
                Required('client_flag'): bool,
                Optional('allow_localhost'): bool,
                Optional('allow_subdomains'): bool,
                Optional('allow_any_name'): bool,
                Optional('allow_ip_sans'): bool,
                Optional('enforce_hostnames'): bool,
                Optional('generate_lease'): bool,
                Optional('no_store'): bool,
                Optional('allowed_domains'): [Match(r'^(?![-.])[a-zA-Z0-9-\.]+(?<![.-])$')],
            }
        }],
        Optional('policies', default=[]): [{
            Required('name'): Match(MOUNT_PATH_REGEX, msg="Must be lowercase alphanumberic string"),
            Required('policy'): str
        }]
    }
})

KeyValueSchema = Schema({
    Required('kind'): All('KV', msg="Must be 'KV'"),
    Required('metadata'): {
        Required('name'): Match(MOUNT_PATH_REGEX, msg="Must be lowercase alphanumberic string"),
        Required('description'): str
    },
    Required('spec'): {
        Optional("config"): {
            Optional('default_lease_ttl', default='8766h'): Match(r'\d+[hms]'),
            Optional('max_lease_ttl', default='17532h'): Match(r'\d+[hms]'),
            Optional('force_no_cache', default=False): bool
        },
        Required("options"): {
            Required("version"): All(Any(1, "1", msg="Must be '1'"), Coerce(str))
        }
    }
})
