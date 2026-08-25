# Getting Your Credentials

UNSTABLE TARGET WARNING — Last verified: 2026-08-25 (26/26 live checks passed).
Jio AI Cloud has no public API; endpoints change without notice and can break
at any time. Check [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for current status.

---

This guide shows you how to extract the three session values the SDK needs
**from your own Jio AI Cloud account**, then validate and store them locally.

## Prerequisites

- **Your own Jio AI Cloud account only.** Extracting another person's session
  credentials without authorization is illegal and explicitly against this
  project's terms ([DISCLAIMER.md](DISCLAIMER.md)).
- Chrome or any Chromium browser (Edge works identically).
- About two minutes.

The three values:

| config.json key | HTTP header | Looks like |
|---|---|---|
| `auth_token` | `Authorization` | `Basic <long base64 string>` |
| `user_id` | `X-User-Id` | 32-char hex |
| `device_key` | `X-Device-Key` | UUID |

> The SDK also sends `X-Api-Key` / `X-App-Secret`, but those are public
> web-app constants baked into every Jio AI Cloud web session — not secrets,
> already defaulted inside `jiocloud/auth.py`. You never need to extract them.

## Method 1 — Copy as cURL (most reliable, recommended)

This reads straight out of the Network tab, so it works no matter how the app
makes its requests — no script injection, nothing that a page reload or an
iframe can break. On Windows the helper reads the clipboard automatically:
you copy, then run one command.

**Step 1 — filter the Network tab** so you only see what matters. Type this
into the filter box at the top of the Network tab:

```
domain:api.jioaicloud.com security/users
```

That isolates the profile endpoint directly. Broader options:

| Filter | Shows |
|---|---|
| `domain:jioaicloud.com` | every Jio AI Cloud API call (all subdomains) |
| `domain:api.jioaicloud.com` | account-level API calls only |
| `domain:api.jioaicloud.com security/users` | just the profile endpoint — ideal for step 2 |

**Step 2 — copy it:** right-click any request in the filtered list →
**Copy → Copy as cURL** (`bash` or `CMD` variant both work; the parser
handles Chrome's caret-escaped Windows output).

**Step 3 — run the helper** (it reads the cURL straight from your clipboard):

```bash
python examples/setup_credentials.py --from-curl
```

That's it. It extracts `Authorization`, `X-User-Id`, and `X-Device-Key`,
calls `GET /security/users` to verify the session live, prints your profile
name/email on success, and writes `config.json`.

Alternatives if the clipboard route is unavailable:

```bash
# save the copied command to a file first
python examples/setup_credentials.py --from-curl --curl-file curl.txt

# paste manually instead of clipboard (finish with Ctrl+Z then Enter on Windows)
python examples/setup_credentials.py --from-curl --paste
```

> **Security:** the cURL command contains your full token. Paste it only into
> this local helper, never into chats, issues, screenshots, or any website.
> If you saved it to a file, delete that file afterwards.

## Method 2 — One-paste console script

1. Log in at <https://www.jioaicloud.com>.
2. Press **F12** → open the **Console** tab. In the context dropdown at the
   top of the console, make sure **top** is selected (not an iframe such as
   the Office document viewer).
3. Paste the entire contents of
   [`examples/browser_console_extractor.js`](https://github.com/Ns81000/jiocloud_client/blob/main/examples/browser_console_extractor.js)
   and press Enter. A pink toast appears in the top-right corner of the page.
4. **Do not reload the page** — reloading (F5) wipes the watcher. Instead,
   click around *inside* the app: open *My Files*, open and close a file.
5. When all three values are found, the toast turns green showing truncated
   values, and the full config JSON is printed in the Console.
6. Run `python examples/setup_credentials.py`, paste the values when prompted;
   it validates them live and writes `config.json`.

<details>
<summary>The one-paste script (same as <code>examples/browser_console_extractor.js</code>)</summary>

The canonical copy lives in
[`examples/browser_console_extractor.js`](https://github.com/Ns81000/jiocloud_client/blob/main/examples/browser_console_extractor.js)
— use that file as the source of truth. It wraps `window.fetch` and
`XMLHttpRequest.setRequestHeader`, inspects request headers of every call to
a `*.jioaicloud.com` URL, shows live progress on an on-page overlay (so it
works even when the console filters output), restores everything afterwards,
and times out after 30 seconds pointing you at Method 1.

</details>

**Known limitation (v1 lesson):** if you reload the page after pasting, the
injected watchers are gone — that is why v2 shows an on-page toast and warns
against F5. If the app's requests come from inside a same-origin iframe
(e.g. the Collabora office viewer), run the paste with the console context
set to `top`; the REST calls still pass through the top window's fetch.

## Validate and Store

```bash
python examples/setup_credentials.py          # interactive prompts
# or, from a Copy-as-cURL capture:
python examples/setup_credentials.py --from-curl --curl-file curl.txt
```

Either path will:

1. Collect the three values (prompted, or parsed from the cURL string).
2. Call `GET https://api.jioaicloud.com/security/users` with the constructed
   headers and print your profile name / email on success.
3. Write `config.json` next to the SDK (refuses to overwrite an existing file
   unless you pass `--force`).
4. Print file-permission guidance (`chmod 600` on Linux/macOS; applied
   automatically there).

A `401 TEJGA0401` during validation means the token was already logged out or
expired — re-extract and retry.

## Verify

```bash
python cli.py info
```

You should see your account name and quota breakdown.

## Safety Rules

- Credentials are for **your own account** and stay on **your machine**.
- They are transmitted **only** to official `*.jioaicloud.com` hosts over TLS.
- This project has zero telemetry and never writes credentials elsewhere.
- Never commit `config.json` (already `.gitignore`d) and never paste tokens
  into issues, screenshots, or chats. If leaked, log out of the web session —
  that revokes the token immediately.
