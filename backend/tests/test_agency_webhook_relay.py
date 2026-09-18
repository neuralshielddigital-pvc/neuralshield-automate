"""Public boundary contract, using only in-process synthetic requests."""
import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def relay(monkeypatch):
    path = Path(__file__).resolve().parents[2] / 'ops/agency-provider-sandbox/webhook_relay.py'
    spec = importlib.util.spec_from_file_location('agency_webhook_relay', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    monkeypatch.setattr(module, 'forward_webhook', lambda body, sig: calls.append((body, sig)) or 200)
    with TestClient(module.create_app(), base_url='http://temporary.example') as client:
        yield module, client, calls


SIGNATURE = 'ts=1234567890;h1=' + 'a' * 64
HEADERS = {'Content-Type': 'application/json', 'Paddle-Signature': SIGNATURE}


@pytest.mark.parametrize('method,path', [
    ('GET', '/'), ('GET', '/health'), ('GET', '/member/'),
    ('GET', '/checkout-config'), ('GET', '/docs'), ('GET', '/openapi.json'),
    ('POST', '/agency-member/consume'), ('GET', '/agency-member/resources/starter'),
    ('GET', '/api/paddle/webhook'), ('OPTIONS', '/api/paddle/webhook'),
    ('POST', '/api/paddle/webhook/'), ('POST', '/api/paddle/webhook?target=http://evil'),
    ('POST', '/api/paddle/%77ebhook'),
])
def test_only_exact_post_path_reaches_backend(relay, method, path):
    _, client, calls = relay
    assert client.request(method, path, content=b'{}', headers=HEADERS).status_code == 404
    assert calls == []


def test_raw_body_and_signature_preserved_but_no_other_headers_forwarded(relay):
    _, client, calls = relay
    body = b'{ "signed": "exact bytes", "newline": true }\n'
    response = client.post('/api/paddle/webhook', content=body, headers={
        **HEADERS, 'Authorization': 'Bearer synthetic-untrusted',
        'Cookie': 'synthetic=untrusted', 'X-Forwarded-Host': 'evil.example',
    })
    assert response.status_code == 200
    assert calls == [(body, SIGNATURE)]
    assert response.json() == {'received': True}
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('headers,body,status', [
    ({'Content-Type': 'application/json'}, b'{}', 401),
    ({**HEADERS, 'Paddle-Signature': 'garbage'}, b'{}', 401),
    ({**HEADERS, 'Origin': 'https://evil.example'}, b'{}', 403),
    ({**HEADERS, 'Content-Type': 'text/plain'}, b'{}', 415),
    ({**HEADERS, 'Content-Encoding': 'gzip'}, b'{}', 415),
    (HEADERS, b'', 400),
    (HEADERS, b'x' * 1_048_577, 413),
])
def test_invalid_requests_never_reach_backend(relay, headers, body, status):
    _, client, calls = relay
    assert client.post('/api/paddle/webhook', content=body, headers=headers).status_code == status
    assert calls == []


@pytest.mark.parametrize('upstream,expected', [(200, 200), (401, 401), (503, 503), (302, 502), (500, 502)])
def test_upstream_status_is_sanitized(relay, monkeypatch, upstream, expected):
    module, client, _ = relay
    monkeypatch.setattr(module, 'forward_webhook', lambda *args: upstream)
    response = client.post('/api/paddle/webhook', content=b'{}', headers=HEADERS)
    assert response.status_code == expected
    assert response.json() == {'received': upstream == 200}
    assert 'location' not in response.headers


def test_backend_error_does_not_expose_details(relay, monkeypatch):
    module, client, _ = relay
    def fail(*args):
        raise OSError('synthetic-sensitive-diagnostics')
    monkeypatch.setattr(module, 'forward_webhook', fail)
    response = client.post('/api/paddle/webhook', content=b'{}', headers=HEADERS)
    assert response.status_code == 502
    assert 'sensitive' not in response.text


def test_fixed_http_destination_host_and_connection_cleanup(monkeypatch):
    path = Path(__file__).resolve().parents[2] / 'ops/agency-provider-sandbox/webhook_relay.py'
    spec = importlib.util.spec_from_file_location('relay_transport', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    class Connection:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))
        def request(self, *args, **kwargs):
            calls.append((args, kwargs))
        def getresponse(self):
            return type('Response', (), {'status': 503})()
        def close(self):
            calls.append('closed')
    monkeypatch.setattr(module.http.client, 'HTTPConnection', Connection)
    assert module.forward_webhook(b'raw', SIGNATURE) == 503
    assert calls[0] == (('api', 8097), {'timeout': 4})
    assert calls[1] == (('POST', '/api/paddle/webhook'), {'body': b'raw', 'headers': {
        'Host': 'localhost', 'Content-Type': 'application/json',
        'Paddle-Signature': SIGNATURE, 'Connection': 'close',
    }})
    assert calls[2] == 'closed'
