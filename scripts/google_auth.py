"""One-time local Google OAuth (installed-app loopback flow, stdlib only).

Creates GOOGLE_TOKEN_FILE with a refresh token. Read-only Calendar + Gmail by default;
pass --calendar-write to also request calendar.events (needed only for approved event creation).
Usage: backend/.venv/bin/python scripts/google_auth.py [--calendar-write]
NOTE: untested against a live Google project in this repo — see README "Integration status".
"""
import http.server
import json
import secrets
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import settings  # noqa: E402
from app.connectors.google_auth import SCOPES, TOKEN_URL, WRITE_SCOPE  # noqa: E402

PORT = 8765
REDIRECT = f"http://127.0.0.1:{PORT}/"


def main():
    if not (settings.google_client_id and settings.google_client_secret):
        sys.exit("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env (OAuth client type: Desktop app).")
    scopes = SCOPES + ([WRITE_SCOPE] if "--calendar-write" in sys.argv else [])
    state = secrets.token_urlsafe(16)
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": settings.google_client_id, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": " ".join(scopes), "access_type": "offline", "prompt": "consent", "state": state})
    result = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"NOVA: authorization received. You can close this tab.")

        def log_message(self, *a):
            pass

    print("Opening browser for Google consent...\n", url)
    webbrowser.open(url)
    srv = http.server.HTTPServer(("127.0.0.1", PORT), H)
    srv.handle_request()
    if result.get("state") != state or "code" not in result:
        sys.exit(f"Authorization failed: {result}")
    r = requests.post(TOKEN_URL, data={"code": result["code"], "client_id": settings.google_client_id,
                                       "client_secret": settings.google_client_secret, "redirect_uri": REDIRECT,
                                       "grant_type": "authorization_code"}, timeout=10)
    r.raise_for_status()
    tok = r.json()
    tok["expires_at"] = time.time() + int(tok.get("expires_in", 3600))
    settings.google_token_file.parent.mkdir(parents=True, exist_ok=True)
    settings.google_token_file.write_text(json.dumps(tok))
    print(f"Saved token to {settings.google_token_file} (gitignored). Scopes: {tok.get('scope')}")


if __name__ == "__main__":
    main()
