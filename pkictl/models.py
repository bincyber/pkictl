from urllib.parse import urljoin


class CertificateAuthority:
    def __init__(self, baseurl, manifest):
        self.baseurl = baseurl
        self.dict = manifest
        self.name = manifest['metadata']['name']
        self.description = manifest['metadata']['description']

    @property
    def spec(self):
        spec = self.dict['spec'].copy()

        subject = spec.get('subject')
        if subject:
            spec.pop('subject')
            spec.update(subject)
        return spec

    @property
    def backend(self):
        return {'type': 'pki', 'description': self.description, 'config': {'max_lease_ttl': self.ttl}}

    @property
    def ttl(self):
        return self.spec['ttl']

    @property
    def config_url(self):
        return urljoin(self.baseurl, f"/v1/{self.name}/config/urls")

    @property
    def ca_urls(self):
        return {
            'issuing_certificates': f'{self.baseurl}/v1/{self.name}/ca',
            'crl_distribution_points': f'{self.baseurl}/v1/{self.name}/crl',
        }


class RootCA(CertificateAuthority):
    def __init__(self, baseurl, manifest):
        super().__init__(baseurl, manifest)

    @property
    def url(self):
        return urljoin(self.baseurl, f"/v1/{self.name}/root/generate/internal")


class IntermediateCA(CertificateAuthority):
    def __init__(self, baseurl, manifest):
        super().__init__(baseurl, manifest)
        self._csr = None
        self._private_key = None
        self._cert = None

    @property
    def issuer(self):
        return self.dict['metadata']['issuer']

    @property
    def kv_engine(self):
        return self.dict['metadata']['kv_engine']

    @property
    def catype(self):
        return self.spec['type']

    @property
    def csr(self):
        return self._csr

    @csr.setter
    def csr(self, value):
        self._csr = value

    @property
    def cert(self):
        return self._cert

    @cert.setter
    def cert(self, value):
        self._cert = value

    @property
    def private_key(self):
        return {'private_key': self._private_key}

    @private_key.setter
    def private_key(self, value):
        self._private_key = value

    @property
    def url(self):
        return urljoin(self.baseurl, f"/v1/{self.name}/intermediate/generate/{self.catype}")

    @property
    def crl_config_url(self):
        return urljoin(self.baseurl, f"/v1/{self.name}/config/crl")

    @property
    def issuer_sign_url(self):
        return urljoin(self.baseurl, f"/v1/{self.issuer}/root/sign-intermediate")

    @property
    def set_signed_url(self):
        return urljoin(self.baseurl, f"/v1/{self.name}/intermediate/set-signed")

    @property
    def kv_engine_url(self):
        return urljoin(self.baseurl, f"/v1/{self.kv_engine}/{self.name}")

    @property
    def spec(self):
        spec = self.dict['spec'].copy()

        subject = spec.get('subject')
        if subject:
            spec.pop('subject')
            spec.update(subject)
        if spec.get('crl'):
            spec.pop('crl')
        if spec.get('roles'):
            spec.pop('roles')
        if spec.get('policies'):
            spec.pop('policies')
        return spec

    @property
    def crl_config(self):
        return self.dict['spec']['crl']

    @property
    def roles(self):
        return self.dict['spec']['roles']

    @property
    def policies(self):
        return self.dict['spec']['policies']


class KeyValueEngine:
    def __init__(self, baseurl, manifest):
        self.baseurl = baseurl
        self.dict = manifest
        self.name = manifest['metadata']['name']

    @property
    def spec(self):
        spec = self.dict['spec'].copy()
        spec.update({
            'type': self.dict['kind'].lower(),
            'description': self.dict['metadata']['description']
        })
        return spec

    @property
    def url(self):
        return urljoin(self.baseurl, f"v1/sys/mounts/{self.name}")
