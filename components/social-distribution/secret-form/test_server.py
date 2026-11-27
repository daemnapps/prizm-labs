import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

spec = importlib.util.spec_from_file_location('receiver', Path(__file__).with_name('server.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ReceiverTests(unittest.TestCase):
    def test_encrypted_one_time_save_and_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('UNRELATED=keep\nGEELARK_API_TOKEN=old\n')
            server = m.Receiver(('127.0.0.1', 0), path)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            url = 'http://127.0.0.1:' + str(server.server_port)
            def request(body, ticket):
                return urllib.request.urlopen(urllib.request.Request(url + '/save', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'Origin': url, 'Authorization': 'Bearer ' + ticket}), timeout=5)
            try:
                with self.assertRaises(urllib.error.HTTPError) as rejected:
                    request({}, 'wrong')
                self.assertEqual(rejected.exception.code, 403)
                key = AESGCM.generate_key(bit_length=256)
                iv = b'123456789012'
                wrapped = server.key.public_key().encrypt(key, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
                ciphertext = AESGCM(key).encrypt(iv, json.dumps({'GEELARK_API_TOKEN':'dummy-test-token'}).encode(), None)
                b64 = lambda v: base64.b64encode(v).decode()
                body = {'wrappedKey':b64(wrapped),'iv':b64(iv),'ciphertext':b64(ciphertext)}
                ticket = server.ticket
                self.assertEqual(json.load(request(body, ticket)), {'saved':True})
                self.assertEqual(path.read_text(), "UNRELATED=keep\nGEELARK_API_TOKEN='dummy-test-token'\n")
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                with self.assertRaises(urllib.error.HTTPError) as replay:
                    request(body, ticket)
                self.assertEqual(replay.exception.code, 410)
            finally:
                server.shutdown()
                server.server_close()

    def test_rejects_environment_injection(self):
        for value in ['abc\nOTHER=value', "abc'", 'abc\\def']:
            with self.assertRaises(ValueError):
                m.validate({'GEELARK_API_TOKEN':value})
        with self.assertRaises(ValueError):
            m.validate({'GEELARK_API_TOKEN':'ok', 'UNRELATED':'bad'})


if __name__ == '__main__':
    unittest.main()
