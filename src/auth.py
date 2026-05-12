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

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .config import Config

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


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
        flow = InstalledAppFlow.from_client_secrets_file(str(Config.CREDENTIALS_FILE), SCOPES)
        print(f"Starting OAuth server on localhost:{port}.")
        print(f"Open this URL in your browser (use http://localhost:{port} for the callback):")
        creds = flow.run_local_server(
            host="localhost",
            port=port,
            open_browser=False,
            redirect_uri_trailing_slash=False,
        )
        print("Authentication successful.")

    Config.TOKEN_FILE.write_text(creds.to_json())
    print(f"Token saved to {Config.TOKEN_FILE}")
    print("You can now copy token.json to the server.")


if __name__ == "__main__":
    authenticate()
