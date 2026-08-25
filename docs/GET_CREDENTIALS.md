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

## Method 1 — One-Paste Console Script (recommended)

1. Log in at <https://www.jioaicloud.com>.
2. Press **F12** → open the **Console** tab.
3. Paste the entire contents of
   [`examples/browser_console_extractor.js`](https://github.com/Ns81000/jiocloud_client/blob/main/examples/browser_console_extractor.js)
   and press Enter. (Canonical copy lives in that file; the block below is the
   same script.)
4. While it watches (about 20 seconds), click around the app — open *My Files*,
   or just press F5 — so it fires API calls.
5. It prints your three values as ready-to-paste JSON:

```json
{
  "auth_token": "Basic ...",
  "user_id": "...",
  "device_key": "..."
}
```

6. Run `python examples/setup_credentials.py` and paste the values when
   prompted — it validates them live and writes `config.json`. Or skip the
   helper and paste the JSON into `config.json` yourself (copy
   `config.example.json` first).

<details>
<summary>The one-paste script (same as <code>examples/browser_console_extractor.js</code>)</summary>

```javascript
(function () {
  "use strict";
  var FOUND = {}, CAPTURED_URLS = 0, DONE = false;
  var NEEDED = ["authorization", "x-user-id", "x-device-key"];
  function label(n){return {authorization:"auth_token","x-user-id":"user_id","x-device-key":"device_key"}[n]||n;}
  function record(headers){
    if(!headers) return;
    CAPTURED_URLS++;
    Object.keys(headers).forEach(function(k){
      var lk=k.toLowerCase();
      if(NEEDED.indexOf(lk)!==-1 && !FOUND[lk]) FOUND[lk]=headers[k];
    });
    if(!DONE && NEEDED.every(function(h){return FOUND[h];})){DONE=true;report();}
  }
  var origFetch = window.fetch;
  window.fetch = function(){
    try{
      var input=arguments[0];
      var url=(typeof input==="string")?input:(input&&input.url)?input.url:String(input);
      var init=arguments[1]||{}, headers={}, hsrc=init.headers||(input&&input.headers);
      if(hsrc){
        if(typeof hsrc.forEach==="function"){hsrc.forEach(function(v,k){headers[k]=v;});}
        else if(typeof hsrc==="object"){Object.keys(hsrc).forEach(function(k){headers[k]=hsrc[k];});}
      }
      if(/jioaicloud\.com/i.test(url)) record(headers);
    }catch(e){}
    return origFetch.apply(this,arguments);
  };
  var origOpen=XMLHttpRequest.prototype.open,
      origSet=XMLHttpRequest.prototype.setRequestHeader,
      origSend=XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open=function(m,u){this.__jc_url=u;this.__jc_headers={};return origOpen.apply(this,arguments);};
  XMLHttpRequest.prototype.setRequestHeader=function(n,v){
    try{if(this.__jc_headers&&/jioaicloud\.com/i.test(this.__jc_url||""))this.__jc_headers[n]=v;}catch(e){}
    return origSet.apply(this,arguments);};
  XMLHttpRequest.prototype.send=function(){
    try{if(/jioaicloud\.com/i.test(this.__jc_url||""))record(this.__jc_headers);}catch(e){}
    return origSend.apply(this,arguments);};
  function report(){
    var auth=String(FOUND["authorization"]).trim();
    if(!/^basic\s/i.test(auth)) auth="Basic "+auth;
    console.log("=== Jio AI Cloud credentials captured ===");
    console.log(JSON.stringify({auth_token:auth,user_id:String(FOUND["x-user-id"]).trim(),
      device_key:String(FOUND["x-device-key"]).trim()},null,2));
    console.log("Requests inspected:",CAPTURED_URLS);
    restore();
  }
  function restore(){try{window.fetch=origFetch;
    XMLHttpRequest.prototype.open=origOpen;
    XMLHttpRequest.prototype.setRequestHeader=origSet;
    XMLHttpRequest.prototype.send=origSend;}catch(e){}}
  console.log("[Jio extractor] Watching *.jioaicloud.com requests...");
  console.log("NOW CLICK AROUND THE APP or press F5 to trigger API calls.");
  setTimeout(function(){
    if(!DONE && Object.keys(FOUND).length>0){DONE=true;report();}
    else if(!DONE){console.warn("[Jio extractor] Nothing captured - use Method 2 below.");restore();}
  },20000);
})();
```

</details>

**How it works:** before any request fires, the script wraps `window.fetch`
and `XMLHttpRequest.setRequestHeader`. Every call to a `*.jioaicloud.com` URL
has its request headers inspected, and the three needed values are captured
the moment they appear. It restores the originals afterwards and touches
nothing else. Everything happens in your browser — nothing is transmitted
anywhere by the script itself.

## Method 2 — Manual Network Tab (works even if Method 1 captures nothing)

1. Log in at <https://www.jioaicloud.com>.
2. Press **F12** → open the **Network** tab.
3. Press F5 or click around so requests appear.
4. Click any request whose URL contains `jioaicloud.com`.
5. In the right pane, open **Headers → Request Headers** and copy:
   - `Authorization:` → everything including the word `Basic` → `auth_token`
   - `X-User-Id:` → `user_id`
   - `X-Device-Key:` → `device_key`
6. Continue with step 6 above.

Tip (Chrome): instead of copying manually, right-click the request →
**Copy → Copy as cURL**, paste into a text editor, and pick the three header
values out of it. Never share that cURL string anywhere — it contains your token.

## Validate and Store: `setup_credentials.py`

```bash
python examples/setup_credentials.py
```

It will:

1. Prompt for the three values.
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
