#!/usr/bin/env python3
"""Short-lived, write-only GeeLark secret receiver. Never logs submitted data."""
import argparse
import base64
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

HERE = Path(__file__).resolve().parent
ALLOWED = {'GEELARK_API_TOKEN', 'PROXY_DE_1'}


def save_env(path, values):
    """Preserve unrelated settings and replace secrets atomically with mode 0600."""
    if path.is_symlink():
        raise ValueError('Unsupported destination')
    old = ''
    if path.exists():
        if not stat.S_ISREG(path.stat().st_mode):
            raise ValueError('Unsupported destination')
        old = path.read_text()
    lines = [line for line in old.splitlines()
             if not re.match(r'^\s*(?:export\s+)?(?:' + '|'.join(values) + r')\s*=', line)]
    # These values cannot contain quotes/newlines; see validate().
    lines += [f"{name}='{value}'" for name, value in values.items()]
    fd, temp = tempfile.mkstemp(prefix='.geelark-env-', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as out:
            out.write('\n'.join(lines) + '\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def validate(values):
    if not isinstance(values, dict) or not values or set(values) - ALLOWED:
        raise ValueError('Unsupported fields')
    if not values.get('GEELARK_API_TOKEN'):
        raise ValueError('API token required')
    for name, value in values.items():
        if not isinstance(value, str) or not 1 <= len(value) <= 4096:
            raise ValueError('Invalid value')
        if any(ord(c) < 33 or ord(c) > 126 or c in "'\"\\" for c in value):
            raise ValueError('Remove spaces or quotes; URL-encode proxy credentials')
    if 'PROXY_DE_1' in values:
        from urllib.parse import urlsplit
        p = urlsplit(values['PROXY_DE_1'])
        if p.scheme not in ('socks5', 'http', 'https') or not p.hostname or not p.port:
            raise ValueError('Invalid proxy URL')
    return values


class Receiver(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, destination, ttl=1800):
        super().__init__(address, Handler)
        self.destination = destination
        self.ticket = secrets.token_urlsafe(32)
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
        self.expires = time.monotonic() + ttl
        self.used = False
        self.lock = threading.Lock()
        self.failures = 0


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body, kind='application/json'):
        raw = body.encode()
        self.send_response(status)
        self.send_header('Content-Type', kind + '; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.server.used or time.monotonic() > self.server.expires:
            return self.reply(410, '{"error":"This form has closed."}')
        if self.path == '/':
            html = (HERE / 'index.html').read_text().replace('__PUBLIC_KEY__', self.server.public_key)
            return self.reply(200, html, 'text/html')
        return self.reply(404, '{}')

    def do_POST(self):
        s = self.server
        if self.path != '/save':
            return self.reply(404, '{}')
        origin = self.headers.get('Origin', '')
        host = self.headers.get('Host', '')
        if origin not in ('https://' + host, 'http://' + host):
            return self.reply(403, '{"error":"Invalid origin."}')
        with s.lock:
            if s.used or time.monotonic() > s.expires or s.failures >= 20:
                return self.reply(410, '{"error":"This form has closed."}')
            if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + s.ticket):
                s.failures += 1
                return self.reply(403, '{"error":"Open the complete private link."}')
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 1 <= size <= 20000:
                    raise ValueError()
                self.connection.settimeout(10)
                payload = json.loads(self.rfile.read(size))
                wrapped = base64.b64decode(payload['wrappedKey'], validate=True)
                nonce = base64.b64decode(payload['iv'], validate=True)
                ciphertext = base64.b64decode(payload['ciphertext'], validate=True)
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                aes = s.key.decrypt(wrapped, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
                values = validate(json.loads(AESGCM(aes).decrypt(nonce, ciphertext, None)))
            except Exception:
                s.failures += 1
                return self.reply(400, '{"error":"Could not save. Check the token and proxy format, then retry."}')
            try:
                save_env(s.destination, values)
            except Exception:
                return self.reply(500, '{"error":"Could not write the local secrets file."}')
            s.used = True
            s.ticket = ''
            s.key = None
            print('Saved secret fields: ' + ', '.join(sorted(values)), flush=True)
            self.reply(200, '{"saved":true}')
            threading.Timer(20, s.shutdown).start()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--destination', type=Path, default=HERE.parents[2] / '.env')
    args = parser.parse_args()
    server = Receiver(('127.0.0.1', args.port), args.destination)
    link_file = HERE.parents[2] / 'output' / 'geelark' / 'form-ticket'
    link_file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(link_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as out:
        out.write(server.ticket)
    timer = threading.Timer(1800, server.shutdown)
    timer.daemon = True
    timer.start()
    print(f'One-time receiver ready on loopback port {args.port}; expires in 30 minutes.', flush=True)
    try:
        server.serve_forever()
    finally:
        timer.cancel()
        server.server_close()
        link_file.unlink(missing_ok=True)
        print('Receiver closed.', flush=True)


if __name__ == '__main__':
    main()
