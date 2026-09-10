"""One local-only HTTP client. Ignore proxy settings and refuse redirects."""
import json
import urllib.request
from config import MAX_RESPONSE_BYTES

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('The local AI server attempted a redirect; request stopped.')

def call_ollama(endpoint, payload):
    if endpoint not in {'chat', 'generate'}:
        raise ValueError('Unsupported local AI endpoint.')
    request = urllib.request.Request(
        f'http://127.0.0.1:11434/api/{endpoint}',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}, method='POST')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=180) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError('Local AI response exceeded the size limit.')
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError('Invalid local AI response.')
    if result.get('error'):
        raise ValueError(str(result['error'])[:500])
    return result
