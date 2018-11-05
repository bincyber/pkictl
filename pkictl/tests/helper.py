from pkictl.models import RootCA, IntermediateCA, KeyValueEngine
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import StringIO
from threading import Thread
import json
import sys
import yaml


ROOT_MANIFEST_YAML         = 'pkictl/tests/manifests/multi/root.yaml'
INTERMEDIATE_MANIFEST_YAML = 'pkictl/tests/manifests/multi/intermediate.yaml'
KV_MANIFEST_YAML           = 'pkictl/tests/manifests/multi/kv.yaml'
PKI_MANIFEST_YAML          = 'pkictl/tests/manifests/pki.yaml'


@contextmanager
def capture_stdout(command, *args, **kwargs):
    out, sys.stdout = sys.stdout, StringIO()
    try:
        command(*args, **kwargs)
        sys.stdout.seek(0)
        yield sys.stdout.read()
    finally:
        sys.stdout = out


class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)

        elif self.path == "/403":
            self.send_response(403)

        elif self.path == "/404":
            self.send_response(404)

        self.send_header('Content-type', 'text/html')
        self.end_headers()
        return


def create_test_http_server():
    server = HTTPServer(('localhost', 8222), TestHandler)
    server.allow_reuse_address = True
    thread = Thread(target=server.serve_forever, args=[0.01])
    thread.setDaemon(True)
    thread.start()
    return server


def get_test_root_ca(baseurl):
    with open(ROOT_MANIFEST_YAML) as f:
        d = yaml.load(f.read())
    return RootCA(baseurl, d)


def get_test_intermediate_ca(baseurl):
    with open(INTERMEDIATE_MANIFEST_YAML) as f:
        d = yaml.load(f.read())
    return IntermediateCA(baseurl, d)


def get_test_kv_engine(baseurl):
    with open(KV_MANIFEST_YAML) as f:
        d = yaml.load(f.read())
    return KeyValueEngine(baseurl, d)


def serialize_json(data):
    return json.dumps(data).encode('utf-8')
