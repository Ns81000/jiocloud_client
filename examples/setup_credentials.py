#!/usr/bin/env python3
"""
Interactive credential setup for the Jio AI Cloud SDK.

What it does:
  1. Prompts you for the three session values (auth_token, user_id, device_key).
  2. LIVE-validates them by calling GET https://api.jioaicloud.com/security/users
     and prints your profile name / email on success.
  3. Writes config.json next to this project (refuses to overwrite unless --force).
  4. Prints a file-permission note so you can restrict access to your user.

Get the three values with examples/browser_console_extractor.js (one paste into
the Chrome DevTools Console while on jioaicloud.com) or the manual Network-tab
method described in docs/GET_CREDENTIALS.md.

Privacy: the token is validated against the official Jio endpoint only and is
written to local disk only. It is never sent anywhere else. Never commit
config.json, never paste it into chats/issues/screenshots.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Allow running from anywhere: resolve SDK root relative to this file.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from jiocloud.auth import JioCloudAuth  # noqa: E402

VALIDATE_URL = "https://api.jioaicloud.com/security/users"


def parse_curl(raw: str) -> dict:
    """Extract auth_token / user_id / device_key from a 'Copy as cURL' string.

    Handles both POSIX ($'...' with \r) and Windows CMD (^-continuation)
    variants Chrome produces, single or double quotes, and header names in
    any case. Never prints the values.
    """
    # Join continuation lines so regexes see one long string.
    s = raw.replace("\\\r\n", " ").replace("\\\n", " ").replace("^\r\n", " ").replace("^\n", " ")
    s = s.replace("$'\\r'", "").replace("'\\r'", "")

    out = {}
    for m in re.finditer(r"-H\s*['\"]([^'\"]+)['\"]", s):
        hdr = m.group(1)
        name, _, value = hdr.partition(":")
        lk = name.strip().lower()
        if lk == "authorization":
            out["auth_token"] = value.strip()
        elif lk == "x-user-id":
            out["user_id"] = value.strip()
        elif lk == "x-device-key":
            out["device_key"] = value.strip()
    return out


def do_validate_and_write(auth_token: str, user_id: str, device_key: str, force: bool) -> None:
    """Shared tail for both --from-curl and the interactive flow."""
    auth = JioCloudAuth(auth_token=auth_token, user_id=user_id, device_key=device_key)

    peek = auth.peek_token_identity()
    if peek and peek.lower() != user_id.lower():
        print(f"\nWARNING: decoded token identity ({peek[:8]}...) does not match "
              f"user_id ({user_id[:8]}...). Continuing anyway, but double-check.")

    print(f"\nValidating credentials against {VALIDATE_URL} ...")
    try:
        payload = validate(auth)
    except Exception as exc:
        code = getattr(exc, "code", None)
        print("\nVALIDATION FAILED.", file=sys.stderr)
        if code == 401:
            print("401 Unauthorized (TEJGA0401): token expired or logged out.",
                  file=sys.stderr)
            print("Log in again at https://www.jioaicloud.com and re-extract the "
                  "headers (docs/GET_CREDENTIALS.md).", file=sys.stderr)
        else:
            print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
            print("Check that all three values are complete and untruncated.",
                  file=sys.stderr)
        sys.exit(3)

    print("\nSUCCESS - credentials are valid.")
    print(f"Profile: {extract_profile(payload)}")

    config_path = PROJECT_ROOT / "config.json"
    write_config(config_path,
                 {"auth_token": auth_token, "user_id": user_id,
                  "device_key": device_key},
                 force=force)


def prompt_value(label: str, hint: str) -> str:
    print()
    print(f"{label}")
    print(f"  ({hint})")
    value = input("> ").strip()
    if not value:
        print("ERROR: empty value is not allowed.", file=sys.stderr)
        sys.exit(1)
    return value


def validate(auth: "JioCloudAuth") -> dict:
    """Call GET /security/users with constructed headers; return parsed JSON."""
    import urllib.request
    import urllib.error

    req = urllib.request.Request(
        VALIDATE_URL,
        method="GET",
        headers=auth.get_headers(),  # includes required Content-Type + Accept-Language
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


def extract_profile(payload: dict) -> str:
    """Best-effort human-readable summary of the profile response."""
    # Envelope shapes seen in captures: {"data": {...}} or direct object.
    node = payload.get("data", payload) if isinstance(payload, dict) else {}
    name = node.get("name") or node.get("userName") or node.get("displayName") or ""
    email = node.get("email") or node.get("emailId") or node.get("userEmail") or ""
    parts = [p for p in (name, email) if p]
    return " | ".join(parts) if parts else json.dumps(payload)[:200]


def write_config(path: Path, cfg: dict, force: bool) -> None:
    if path.exists() and not force:
        print(f"\nREFUSING to overwrite existing {path}")
        print("Re-run with --force if you really want to replace it.")
        sys.exit(2)
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing config.json")
    parser.add_argument("--show-extractor", action="store_true",
                        help="print the one-paste browser console extractor "
                             "(same as examples/browser_console_extractor.js)")
    parser.add_argument("--from-curl", action="store_true",
                        help="read a 'Copy as cURL' command from stdin (or a "
                             "file path passed after --curl-file) and extract "
                             "the three credential headers from it")
    parser.add_argument("--curl-file", default=None,
                        help="file containing the copied cURL command")
    args = parser.parse_args()

    if args.show_extractor:
        js = Path(__file__).with_name("browser_console_extractor.js")
        print(js.read_text(encoding="utf-8"))
        return

    if args.from_curl:
        if args.curl_file:
            raw = Path(args.curl_file).read_text(encoding="utf-8")
        else:
            print("Paste the 'Copy as cURL' output (right-click the request in")
            print("DevTools Network tab -> Copy -> Copy as cURL), then press Enter:")
            raw = sys.stdin.read()
        vals = parse_curl(raw)
        missing = [k for k in ("auth_token", "user_id", "device_key") if not vals.get(k)]
        if missing:
            print(f"\nERROR: could not find header(s) {missing} in the pasted "
                  "command. Make sure you copied a request TO a "
                  "*.jioaicloud.com URL.", file=sys.stderr)
            sys.exit(4)
        auth_token = f"Basic {vals['auth_token'].removeprefix('Basic ').strip()}"
        user_id, device_key = vals["user_id"], vals["device_key"]
        # fall through to validation + write below
        do_validate_and_write(auth_token, user_id, device_key, args.force)
        return

    print("=" * 62)
    print("Jio AI Cloud SDK - credential setup")
    print("=" * 62)
    print("This validates YOUR session against YOUR account only.")

    raw_token = prompt_value(
        "auth_token",
        "Authorization header from DevTools; 'Basic <base64>' - the Basic prefix is optional",
    ).replace("Basic ", "").replace("basic ", "")
    auth_token = f"Basic {raw_token}"

    user_id = prompt_value(
        "user_id",
        "X-User-Id header; 32-character hex string",
    )
    device_key = prompt_value(
        "device_key",
        "X-Device-Key header; looks like a UUID",
    )

    auth = JioCloudAuth(auth_token=auth_token, user_id=user_id, device_key=device_key)

    peek = auth.peek_token_identity()
    if peek and peek.lower() != user_id.lower():
        print(f"\nWARNING: decoded token identity ({peek[:8]}...) does not match "
              f"user_id ({user_id[:8]}...). Continuing anyway, but double-check.")

    print(f"\nValidating credentials against {VALIDATE_URL} ...")
    try:
        payload = validate(auth)
    except Exception as exc:  # urllib raises HTTPError / URLError
        code = getattr(exc, "code", None)
        print("\nVALIDATION FAILED.", file=sys.stderr)
        if code == 401:
            print("401 Unauthorized (TEJGA0401): token expired or logged out.",
                  file=sys.stderr)
            print("Log in again at https://www.jioaicloud.com and re-extract the "
                  "headers (docs/GET_CREDENTIALS.md).", file=sys.stderr)
        else:
            print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
            print("Check that all three values are complete and untruncated.",
                  file=sys.stderr)
        sys.exit(3)

    print("\nSUCCESS - credentials are valid.")
    print(f"Profile: {extract_profile(payload)}")

    config_path = PROJECT_ROOT / "config.json"
    write_config(config_path,
                 {"auth_token": auth_token, "user_id": user_id,
                  "device_key": device_key},
                 force=args.force)

    print("""
SECURITY NOTES
--------------
config.json contains a live session credential. Protect it:

  Windows : the file is inside your user profile, which is already private
            to your account. Do NOT move it into any synced/shared folder.
  Linux/macOS: run  chmod 600 config.json  to restrict it to your user.

Never commit config.json (it is git-ignored), never paste its contents into
issues, chats, or screenshots. If leaked, log out of the web session to
revoke the token immediately.

Next step:  python cli.py info
""")

    if os.name == "posix":
        try:
            os.chmod(config_path, 0o600)
            print("(chmod 600 applied automatically)")
        except OSError as e:
            print(f"(could not chmod: {e})")


if __name__ == "__main__":
    main()
