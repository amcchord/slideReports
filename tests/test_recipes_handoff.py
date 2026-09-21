import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import Flask, redirect
from lib.recipes_handoff import consume_token, install_handoff

SECRET = "12" * 32
KEY = "tk_demo_private_key"


def make_token(state, audience="chat", **overrides):
    now = int(time.time())
    claims = dict(iss="slide.recipes", aud=audience, state=state, iat=now,
                  exp=now + 60, jti=secrets.token_hex(16), key=KEY)
    claims.update(overrides)
    nonce = secrets.token_bytes(12)
    data = AESGCM(bytes.fromhex(SECRET)).encrypt(nonce, json.dumps(claims).encode(),
            ("slide-recipes:handoff:v1:" + audience).encode())
    return base64.urlsafe_b64encode(nonce + data).decode().rstrip("=")


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "handoffs.sqlite3"
        self.state = secrets.token_urlsafe(32)

    def tearDown(self):
        self.temp.cleanup()

    def consume(self, token, state=None, audience="chat"):
        return consume_token(token, SECRET, audience, state or self.state, self.database)

    def test_encrypted_one_use_token_and_private_receipts(self):
        token = make_token(self.state)
        self.assertNotIn(KEY, token)
        self.assertEqual(self.consume(token), KEY)
        self.assertNotIn(KEY.encode(), self.database.read_bytes())
        self.assertEqual(self.database.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError): self.consume(token)

    def test_reject_tampering_wrong_app_state_and_time(self):
        token = make_token(self.state)
        cases = [token[:50] + ("A" if token[50] != "A" else "B") + token[51:],
                 make_token(self.state, exp=int(time.time()) - 1),
                 make_token(self.state, iat=int(time.time()) + 100),
                 make_token(self.state, exp=int(time.time()) + 600),
                 make_token(self.state, iss="other"),
                 make_token(self.state, key="bad"), "garbage"]
        for value in cases:
            with self.assertRaises(ValueError): self.consume(value)
        with self.assertRaises(ValueError): self.consume(token, state="another-browser")
        with self.assertRaises(ValueError): self.consume(token, audience="reports")

    def test_atomic_single_use_across_concurrent_workers(self):
        token = make_token(self.state)
        def attempt(_):
            try: self.consume(token); return True
            except ValueError: return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(attempt, range(4))), 1)

    def web_app(self):
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY="browser-secret", RECIPES_HANDOFF_KEY=SECRET)
        received = []
        def connect(key):
            received.append(key)
            return redirect("/connected")
        auto = install_handoff(app, "chat", connect, "/manual", self.database)
        @app.get("/auto")
        def auto_status(): return {"auto": auto()}
        return app, received

    def test_browser_bound_origin_and_session_and_fallback(self):
        app, received = self.web_app()
        client = app.test_client()
        self.assertTrue(client.get('/auto').json['auto'])
        response = client.get('/connect/recipes?source=www')
        state = parse_qs(urlparse(response.location).query)['state'][0]
        self.assertTrue(response.location.startswith('https://www.slide.recipes/connectApp.php?'))
        self.assertFalse(client.get('/auto').json['auto'])
        data = {'state': state, 'token': make_token(state)}
        self.assertEqual(app.test_client().post('/connect/recipes/callback', data=data,
            headers={'Origin':'https://www.slide.recipes'}).status_code, 400)
        self.assertEqual(client.post('/connect/recipes/callback', data=data,
            headers={'Origin':'https://attacker.example'}).status_code, 400)
        self.assertEqual(received, [])
        response = client.get('/connect/recipes')
        state = parse_qs(urlparse(response.location).query)['state'][0]
        data = {'state':state,'token':make_token(state)}
        response = client.post('/connect/recipes/callback', data=data, headers={'Origin':'https://slide.recipes'})
        self.assertEqual(response.location, '/connected')
        self.assertEqual(received, [KEY])
        self.assertEqual(client.post('/connect/recipes/callback', data=data, headers={'Origin':'https://slide.recipes'}).status_code,400)
        response=client.get('/connect/recipes?source=https://attacker.example')
        self.assertTrue(response.location.startswith('https://slide.recipes/'))
        state=parse_qs(urlparse(response.location).query)['state'][0]
        response=client.post('/connect/recipes/callback',data={'state':state,'error':'not_connected'},headers={'Origin':'https://slide.recipes'})
        self.assertEqual(response.location,'/manual')
        self.assertFalse(client.get('/auto').json['auto'])


class ReportsHandoffTests(unittest.TestCase):
    def test_connection_reuses_existing_report_database(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
            'ENCRYPTION_KEY':'12'*16, 'FLASK_SECRET_KEY':'test-cookie-secret',
            'CLAUDE_API_KEY':'test-model-key', 'POSTMARK_API_KEY':'',
            'DATA_DIR':folder, 'RECIPES_HANDOFF_KEY':SECRET,
            'RECIPES_HANDOFF_DB':str(Path(folder)/'receipts.sqlite3'),
        }):
            import app as reports
            from lib.database import Database, get_database_path
            reports.app.config.update(TESTING=True, RECIPES_HANDOFF_KEY=SECRET)
            client=reports.app.test_client()
            db=Database(get_database_path(reports.Encryption.hash_api_key(KEY)))
            db.set_preference('preserved_test_preference','keep')
            response=client.get('/connect/recipes')
            state=parse_qs(urlparse(response.location).query)['state'][0]
            with patch('app.SlideAPIClient.test_connection',return_value=True):
                response=client.post('/connect/recipes/callback',data={'state':state,'token':make_token(state,audience='reports')},headers={'Origin':'https://slide.recipes'})
            self.assertEqual(response.location,'/dashboard')
            cookie=client.get_cookie('slide_api_key')
            self.assertEqual(reports.encryption.decrypt(cookie.value),KEY)
            self.assertEqual(db.get_preference('preserved_test_preference'),'keep')
            self.assertEqual(client.get('/').location,'/dashboard')
            client.get('/logout')
            self.assertEqual(client.get('/').location,'/setup')


if __name__ == '__main__': unittest.main()
