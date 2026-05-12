"""One-time Google OAuth setup.

Runs an OAuth flow that listens on a fixed port (default 8080) so it works
both from a local machine and from inside Docker (with `-p 8080:8080`).

For a remote server, open an SSH tunnel from your laptop first:
    ssh -L 8080:localhost:8080 user@server
then point your browser at http://localhost:8080 when prompted.
"""

from __future__ import annotations

import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from .config import Config

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _run_auth_flow(port: int) -> Credentials:
    """Start OAuth flow binding on 0.0.0.0 but using localhost in the redirect URI."""
    redirect_uri = f"http://localhost:{port}"

    flow = Flow.from_client_secrets_file(
        str(Config.CREDENTIALS_FILE),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )

    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    print(f"\nOpen this URL in your browser:\n\n  {auth_url}\n")
    print(f"Waiting for callback on http://localhost:{port} ...")

    callback_url: list[str] = []
    server = HTTPServer(("0.0.0.0", port), BaseHTTPRequestHandler)

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            if "code" in params:
                callback_url.append(f"http://localhost:{port}{self.path}")
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h2>Authentication successful! You can close this tab.</h2>")
            else:
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h2>Missing code parameter.</h2>")
            threading.Thread(target=server.shutdown, daemon=True).start()

        def log_message(self, *args):
            pass

    server = HTTPServer(("0.0.0.0", port), _Handler)
    server.serve_forever()

    flow.fetch_token(authorization_response=callback_url[0])
    return flow.credentials


def authenticate() -> None:
    if not Config.CREDENTIALS_FILE.exists():
        print(f"ERROR: {Config.CREDENTIALS_FILE} not found.")
        print("Download it from Google Cloud Console > APIs & Services > Credentials.")
        sys.exit(1)

    creds = None
    if Config.TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(Config.TOKEN_FILE), SCOPES)

    if creds and creds.valid:
        print(f"Already authenticated. {Config.TOKEN_FILE} is valid.")
        return

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        print("Token refreshed.")
    else:
        port = int(os.getenv("AUTH_PORT", "8080"))
        creds = _run_auth_flow(port)
        print("Authentication successful.")

    Config.TOKEN_FILE.write_text(creds.to_json())
    print(f"Token saved to {Config.TOKEN_FILE}")


if __name__ == "__main__":
    authenticate()
