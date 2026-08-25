/**
 * Jio AI Cloud — one-paste credential extractor (Chrome DevTools Console)
 *
 * HOW TO USE
 * 1. Log in to https://www.jioaicloud.com in Chrome.
 * 2. Press F12, open the Console tab.
 * 3. Paste this ENTIRE file's contents and press Enter.
 * 4. While it captures (about 15 seconds), click around the app — e.g. open
 *    "My Files" or refresh the page with F5 — so it fires API requests.
 * 5. It prints a ready-to-use config.json. Copy it into the project root,
 *    or feed the three values to examples/setup_credentials.py.
 *
 * How it works: window.fetch is wrapped BEFORE any request is made; every
 * response whose URL matches *.jioaicloud.com has its request headers read.
 * If nothing is captured (the app may use XMLHttpRequest or an already-bound
 * fetch), fall back to the Network-tab method in docs/GET_CREDENTIALS.md.
 *
 * Privacy: values are printed to YOUR console only. Nothing is transmitted
 * anywhere by this script. Never paste the output into any chat/issue/page.
 */
(function () {
  "use strict";

  var FOUND = {};           // header name -> value
  var CAPTURED_URLS = 0;
  var NEEDED = ["authorization", "x-user-id", "x-device-key"];
  var DONE = false;

  function label(name) {
    switch (name) {
      case "authorization":  return "auth_token";
      case "x-user-id":      return "user_id";
      case "x-device-key":   return "device_key";
    }
    return name;
  }

  function record(headers) {
    if (!headers) return;
    CAPTURED_URLS++;
    Object.keys(headers).forEach(function (k) {
      var lk = k.toLowerCase();
      if (NEEDED.indexOf(lk) !== -1 && !FOUND[lk]) {
        FOUND[lk] = headers[k];
      }
    });
    if (!DONE && NEEDED.every(function (h) { return FOUND[h]; })) {
      DONE = true;
      report();
    }
  }

  // --- Strategy A: wrap window.fetch --------------------------------------
  if (typeof window.fetch === "function") {
    var origFetch = window.fetch;
    window.fetch = function () {
      var args = arguments;
      try {
        var input = args[0];
        var url = (typeof input === "string") ? input :
                  (input && input.url) ? input.url : String(input);
        var init = args[1] || {};
        var headers = {};
        // Merge Headers object / plain object from the Request or init.
        var hsrc = init.headers || (input && input.headers);
        if (hsrc) {
          if (typeof hsrc.forEach === "function") {
            hsrc.forEach(function (v, k) { headers[k] = v; });
          } else if (typeof hsrc === "object") {
            Object.keys(hsrc).forEach(function (k) { headers[k] = hsrc[k]; });
          }
        }
        if (/jioaicloud\.com/i.test(url)) record(headers);
      } catch (e) { /* never break the app */ }
      return origFetch.apply(this, args);
    };
  }

  // --- Strategy B: wrap XMLHttpRequest.setRequestHeader --------------------
  var xhrState = null; // per-request header bag via onreadystatechange trick
  if (typeof window.XMLHttpRequest === "function") {
    var origOpen = XMLHttpRequest.prototype.open;
    var origSet = XMLHttpRequest.prototype.setRequestHeader;
    var origSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function (method, url) {
      this.__jc_url = url;
      this.__jc_headers = {};
      return origOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.setRequestHeader = function (name, value) {
      try {
        if (this.__jc_headers && /jioaicloud\.com/i.test(this.__jc_url || "")) {
          this.__jc_headers[name] = value;
        }
      } catch (e) { /* ignore */ }
      return origSet.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function () {
      try {
        if (/jioaicloud\.com/i.test(this.__jc_url || "")) record(this.__jc_headers);
      } catch (e) { /* ignore */ }
      return origSend.apply(this, arguments);
    };
  }

  // --- Report --------------------------------------------------------------
  function fmt(v) {
    // Authorization may arrive without the "Basic " prefix; normalize.
    return String(v).trim();
  }

  function report() {
    var auth = fmt(FOUND["authorization"]);
    if (!/^basic\s/i.test(auth)) auth = "Basic " + auth;

    console.log("%c==============================================", "color:#0a0;font-weight:bold");
    console.log("%c Jio AI Cloud credentials captured.", "color:#0a0;font-weight:bold");
    console.log("%c Copy the JSON below into config.json", "color:#0a0");
    console.log("%c (or run: python examples/setup_credentials.py)", "color:#0a0");
    console.log("%c----------------------------------------------", "color:#0a0");
    console.log(JSON.stringify({
      "_comment_1": "auth_token = Authorization header (Basic ...)",
      "_comment_2": "user_id   = X-User-Id header",
      "_comment_3": "device_key= X-Device-Key header",
      "auth_token": auth,
      "user_id": fmt(FOUND["x-user-id"]),
      "device_key": fmt(FOUND["x-device-key"])
    }, null, 2));
    console.log("%c==============================================", "color:#0a0;font-weight:bold");
    console.log("Labeled values:");
    console.log("  auth_token : " + auth.slice(0, 14) + "...(truncated here for safety)");
    console.log("  user_id    : " + fmt(FOUND["x-user-id"]));
    console.log("  device_key : " + fmt(FOUND["x-device-key"]));
    console.log("Requests inspected: " + CAPTURED_URLS);
    restore();
  }

  function restore() {
    // Put original functions back so the app is untouched afterwards.
    try {
      if (origFetchRef) window.fetch = origFetchRef;
      XMLHttpRequest.prototype.open = origOpenRef;
      XMLHttpRequest.prototype.setRequestHeader = origSetRef;
      XMLHttpRequest.prototype.send = origSendRef;
    } catch (e) { /* ignore */ }
  }

  var origFetchRef = (typeof origFetch !== "undefined") ? origFetch : null;
  var origOpenRef  = origOpen, origSetRef = origSet, origSendRef = origSend;

  console.log("%c[Jio extractor] Watching *.jioaicloud.com requests...", "color:#e80;font-weight:bold");
  console.log("%cNOW CLICK AROUND THE APP or press F5 to trigger API calls.", "color:#e80;font-weight:bold");
  console.log("(Fallback: Network tab -> click any jioaicloud request -> Headers -> copy");
  console.log(" Authorization / X-User-Id / X-Device-Key manually.)");

  // Safety net: report whatever was found after 20s even if incomplete.
  setTimeout(function () {
    if (!DONE && Object.keys(FOUND).length > 0) { DONE = true; report(); }
    else if (!DONE) {
      console.warn("[Jio extractor] No matching requests captured. The app may not have fired any calls.");
      console.warn("Try pressing F5 while this is installed, or use the Network tab method in docs/GET_CREDENTIALS.md.");
      restore();
    }
  }, 20000);
})();
