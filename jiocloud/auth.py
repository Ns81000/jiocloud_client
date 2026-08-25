"""
Jio AI Cloud SDK - Authentication & Header Manager

Credentials are loaded ONLY from a local config file or environment variables.
They are never logged, never persisted anywhere else, and never transmitted
to any endpoint other than *.jioaicloud.com / api.jioaicloud.com hosts.
"""

import base64
import json
import os
from pathlib import Path
from typing import Dict, Optional
from .exceptions import AuthenticationError


# Public, app-level constants observed in the official web client bundle.
# These are NOT user credentials: every Jio AI Cloud web session sends them.
DEFAULT_API_KEY = "c153b48e-d8a1-48a0-a40d-293f1dc5be0e"
DEFAULT_APP_SECRET = "ODc0MDE2M2EtNGY0MC00YmU2LTgwZDUtYjNlZjIxZGRkZjlj"
DEFAULT_CLIENT_DETAILS = "clientType:WEB; appVersion:86.0.1"

# Hosts the SDK is permitted to talk to. Any credential leaving this process
# goes only to these hosts over TLS.
ALLOWED_HOSTS = (
    "www.jioaicloud.com",
    "api.jioaicloud.com",
    "jaws-api.jioaicloud.com",
    "jaws-dl.jioaicloud.com",
    "jaws-contacts.jioaicloud.com",
    "jaws-msg.jioaicloud.com",
    "boards.jioaicloud.com",
)


class JioCloudAuth:
    """
    Manages session tokens and constructs verified HTTP request headers
    for Jio AI Cloud API services.
    """

    def __init__(
        self,
        auth_token: str,
        user_id: str,
        device_key: str,
        api_key: str = DEFAULT_API_KEY,
        app_secret: str = DEFAULT_APP_SECRET,
        client_details: str = DEFAULT_CLIENT_DETAILS,
        device_type: str = "W",
        accept_language: str = "en-US,en;q=0.9"
    ):
        if not auth_token:
            raise AuthenticationError("Authorization token (Basic token) cannot be empty.")
        if not user_id:
            raise AuthenticationError("User ID (X-User-Id) cannot be empty.")
        if not device_key:
            raise AuthenticationError("Device Key (X-Device-Key) cannot be empty.")

        # Ensure Basic prefix if omitted
        self.auth_token = auth_token if auth_token.startswith("Basic ") else f"Basic {auth_token}"
        self.user_id = user_id
        self.device_key = device_key
        self.api_key = api_key
        self.app_secret = app_secret
        self.client_details = client_details
        self.device_type = device_type
        self.accept_language = accept_language

    def get_headers(self, content_type: Optional[str] = "application/json; charset=UTF-8") -> Dict[str, str]:
        """Generate standard HTTP headers required by Jio Cloud APIs."""
        headers = {
            "Authorization": self.auth_token,
            "X-User-Id": self.user_id,
            "X-Device-Key": self.device_key,
            "X-Device-Type": self.device_type,
            "X-Api-Key": self.api_key,
            "X-App-Secret": self.app_secret,
            "X-Client-Details": self.client_details,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": self.accept_language,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def peek_token_identity(self) -> Optional[str]:
        """
        Best-effort decode of the Basic token's embedded identity segment
        (format observed: base64(userId#ATK#payload)). Returns the userId
        fragment or None. Never raises; used for local sanity checks only.
        """
        try:
            b64 = self.auth_token.split(" ", 1)[-1]
            raw = base64.b64decode(b64).decode("utf-8", errors="ignore")
            return raw.split("#", 1)[0] or None
        except Exception:
            return None

    @classmethod
    def from_file(cls, config_path: str = "config.json") -> "JioCloudAuth":
        """Load authentication credentials from a JSON configuration file."""
        p = Path(config_path)
        if not p.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            auth_token=data.get("auth_token") or data.get("Authorization", ""),
            user_id=data.get("user_id") or data.get("X-User-Id", ""),
            device_key=data.get("device_key") or data.get("X-Device-Key", ""),
            api_key=data.get("api_key", DEFAULT_API_KEY),
            app_secret=data.get("app_secret", DEFAULT_APP_SECRET),
            client_details=data.get("client_details", DEFAULT_CLIENT_DETAILS),
            device_type=data.get("device_type", "W"),
            accept_language=data.get("accept_language", "en-US,en;q=0.9")
        )

    @classmethod
    def from_env(cls) -> "JioCloudAuth":
        """Load authentication credentials from environment variables."""
        auth_token = os.environ.get("JIOCLOUD_AUTH_TOKEN") or os.environ.get("JIOCLOUD_AUTH")
        user_id = os.environ.get("JIOCLOUD_USER_ID")
        device_key = os.environ.get("JIOCLOUD_DEVICE_KEY")

        if not (auth_token and user_id and device_key):
            raise AuthenticationError(
                "Missing environment variables. Please set JIOCLOUD_AUTH_TOKEN, JIOCLOUD_USER_ID, and JIOCLOUD_DEVICE_KEY."
            )

        return cls(
            auth_token=auth_token,
            user_id=user_id,
            device_key=device_key,
            api_key=os.environ.get("JIOCLOUD_API_KEY", DEFAULT_API_KEY),
            app_secret=os.environ.get("JIOCLOUD_APP_SECRET", DEFAULT_APP_SECRET),
            client_details=os.environ.get("JIOCLOUD_CLIENT_DETAILS", DEFAULT_CLIENT_DETAILS),
            device_type=os.environ.get("JIOCLOUD_DEVICE_TYPE", "W")
        )
