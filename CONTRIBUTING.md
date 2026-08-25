# Contributing

Thank you for helping keep an unofficial SDK alive against a moving target.

> **UNSTABLE TARGET:** Jio AI Cloud has no public API. Endpoints change
> without notice and can break at any time. Last verified against production:
> **2026-08-25 (26/26 checks)**. Current status always lives in
> [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).

## Reporting a broken endpoint

This is the single most valuable contribution. Open an issue using the
**Endpoint Broken** template with:

1. The endpoint (method + path) and which SDK method/CLI command wraps it.
2. Expected vs actual behavior.
3. The exact server error code (`NMSOM*`, `TEJV*`, `BRSOM*`, `TEJRF0400`,
   `TEJGA0401`, ...) and HTTP status.
4. Whether you can offer a fresh traffic capture (checkbox in the template).

Before filing, check [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) — the issue
may already be documented (for example, `401 TEJGA0401` on every call just
means your session token was revoked by a web logout).

## Submitting capture-based fixes

The protocol is reverse-engineered from real web-client traffic. To propose a
fix:

1. Capture the working request from **your own account's** browser session
   (DevTools → Network → right-click → Copy as cURL).
2. **Redact ruthlessly**: strip `Authorization`, `X-User-Id`, `X-Device-Key`,
   cookies, and any personal object names/paths. We only need the endpoint,
   header *names*, and payload *shape*. Issues and PRs containing live tokens
   will be rejected — rotate your token by logging out if you leak one.
3. Open a PR that updates the relevant code path **and** the docs
   (`docs/API_REFERENCE.md`, and `docs/KNOWN_ISSUES.md` if it resolves or adds
   an issue).
4. If the fix touches `jiocloud/client.py`, update
   [`tests/live_verify.py`](tests/live_verify.py) in the same commit so the
   verification matrix covers the changed contract.

[KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) is the tracking hub: resolved issues
stay there with their history so future contributors understand the contract
drift over time.

## Development setup

```bash
git clone https://github.com/Ns81000/jiocloud_client.git
cd jiocloud_client

# Offline unit tests (no credentials needed)
python -m unittest discover -s tests

# Full 26-check live matrix (requires your own config.json)
python tests/live_verify.py
```

Zero dependencies, Python 3.8+. Please keep it that way for the SDK core.

## Ground rules

- Only ever test against **your own account**.
- Never commit `config.json` (git-ignored) or paste tokens anywhere.
- No emojis in README/docs/site/AI assets (technical ✓ in test-output
  references only).
- Every claim in docs must match verified behavior — invent nothing.
- Keep legal disclaimers intact and visible.
