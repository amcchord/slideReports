"""Recipes handoff v1. Keep this protocol module in sync with slideReports/lib.

Browser-bound state + AES-GCM audience binding + durable single-use receipt.
The credential is never carried in a URL or a shared parent-domain cookie.
"""
from contextlib import closing
import base64
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlencode

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import Blueprint, abort, redirect, request, session


def consume_token(token, secret, audience, state, database):
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]{40,4096}", token):
            raise ValueError()
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        plain = AESGCM(bytes.fromhex(secret)).decrypt(
            raw[:12], raw[12:], ("slide-recipes:handoff:v1:" + audience).encode()
        )
        claims = json.loads(plain)
        now = time.time()
        if (claims["iss"] != "slide.recipes" or claims["aud"] != audience
                or not secrets.compare_digest(claims["state"], state)
                or not now - 65 <= claims["iat"] <= now + 5
                or not now < claims["exp"] <= claims["iat"] + 60
                or not re.fullmatch(r"[a-f0-9]{32}", claims["jti"])
                or not re.fullmatch(r"tk_[A-Za-z0-9_]{7,296}", claims["key"])):
            raise ValueError()
        path = Path(database)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        with closing(sqlite3.connect(path, timeout=10)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS used_handoffs (id TEXT PRIMARY KEY, expires REAL NOT NULL)")
            db.execute("DELETE FROM used_handoffs WHERE expires<?", (now,))
            db.execute("INSERT INTO used_handoffs VALUES (?,?)", (claims["jti"], claims["exp"]))
        return claims["key"]
    except Exception:
        raise ValueError("Connection expired or could not be verified. Reopen this app from Recipes.") from None


def install_handoff(app, audience, connect, fallback, database):
    bp = Blueprint("recipes_handoff", __name__)

    def configured():
        return bool(app.config.get("RECIPES_HANDOFF_KEY"))

    @bp.get("/connect/recipes")
    def begin():
        session["recipes_attempted"] = True
        if not configured():
            return redirect(fallback)
        source = "https://www.slide.recipes" if request.args.get("source") == "www" else "https://slide.recipes"
        state = secrets.token_urlsafe(32)
        pending = session.get("recipes_pending", {})
        pending = {k: v for k, v in pending.items() if v["created"] > time.time() - 300}
        pending = dict(list(pending.items())[-3:])
        pending[state] = {"origin": source, "created": time.time()}
        session["recipes_pending"] = pending
        response = redirect(source + "/connectApp.php?" + urlencode({"app": audience, "state": state}))
        response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        return response

    @bp.post("/connect/recipes/callback")
    def callback():
        if not configured():
            abort(404)
        if request.content_length and request.content_length > 8192:
            abort(413)
        state = request.form.get("state", "")
        pending = session.get("recipes_pending", {})
        expected = pending.pop(state, None)
        session["recipes_pending"] = pending
        if (not expected or expected["created"] < time.time() - 300
                or request.headers.get("Origin") != expected["origin"]):
            abort(400, "Connection expired. Reopen this app from Recipes.")
        if request.form.get("error") in ("not_connected", "unavailable"):
            return redirect(fallback)
        try:
            key = consume_token(request.form.get("token", ""), app.config["RECIPES_HANDOFF_KEY"], audience, state, database)
            response = connect(key)
        except Exception:
            abort(400, "Unable to connect automatically. Reopen this app from Recipes or connect your key manually.")
        response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        return response

    app.register_blueprint(bp)
    return lambda: configured() and not session.get("recipes_attempted")
