/**
 * Jio AI Cloud — one-paste credential extractor v2 (Chrome DevTools Console)
 *
 * HOW TO USE
 * 1. Log in to https://www.jioaicloud.com in Chrome.
 * 2. Press F12, open the Console tab. Make sure the context dropdown at the
 *    top of the console says "top" (not an iframe).
 * 3. Paste this ENTIRE file and press Enter. A pink toast appears top-right.
 * 4. IMPORTANT: do NOT reload the page (F5 wipes the watcher). Instead click
 *    around INSIDE the app: open My Files, Photos, open then close a file.
 * 5. When all three values are found, the toast turns green and shows the
 *    values; the full config.json JSON is printed here in the Console.
 *
 * How it works: window.fetch and XMLHttpRequest are wrapped BEFORE requests
 * fire; request headers of *.jioaicloud.com calls are inspected. Originals
 * are restored afterwards. Nothing is transmitted anywhere by this script.
 *
 * If nothing is captured within 30s, use the cURL method instead:
 * DevTools Network tab -> click any jioaicloud.com request -> right-click ->
 * Copy -> Copy as cURL -> run:  python examples/setup_credentials.py --from-curl
 */
(function () {
  "use strict";

  var FOUND = {};
  var CAPTURED_URLS = 0;
  var NEEDED = ["authorization", "x-user-id", "x-device-key"];
  var DONE = false;

  // ---- On-page toast (works even when console filtering hides logs) ------
  var toast = null, toastLines = {};
  function ensureToast() {
    if (toast) return toast;
    toast = document.createElement("div");
    toast.style.cssText = "position:fixed;top:14px;right:14px;z-index:2147483647;" +
      "background:#b3266e;color:#fff;padding:12px 16px;border-radius:10px;" +
      "font:13px/1.45 monospace;max-width:420px;box-shadow:0 4px 18px rgba(0,0,0,.4);";
    (document.body || document.documentElement).appendChild(toast);
    return toast;
  }
  function setToast(html) { ensureToast().innerHTML = html; }
  function toastState() {
    var have = NEEDED.filter(function (h) { return FOUND[h]; }).length;
    var rows = NEEDED.map(function (h) {
      var v = FOUND[h];
      return "<div>" + (v ? "\u2713" : "\u2022") + " " + h + ": <b>" +
        (v ? String(v).slice(0, 10) + "\u2026" : "waiting") + "</b></div>";
    }).join("");
    setToast("<div style='font-weight:bold;margin-bottom:4px'>Jio extractor: " +
      have + "/3 captured \u2014 now CLICK AROUND the app (do NOT press F5)</div>" + rows);
  }

  function record(headers) {
    if (!headers) return;
    CAPTURED_URLS++;
    Object.keys(headers).forEach(function (k) {
      var lk = String(k).toLowerCase();
      if (NEEDED.indexOf(lk) !== -1 && !FOUND[lk]) {
        FOUND[lk] = String(headers[k]).trim();
      }
    });
    if (!DONE && NEEDED.every(function (h) { return FOUND[h]; })) {
      DONE = true;
      report();
    } else {
      toastState();
    }
  }

  // ---- Strategy A: wrap window.fetch --------------------------------------
  var origFetch = (typeof window.fetch === "function") ? window.fetch : null;
  if (origFetch) {
    window.fetch = function () {
      try {
        var input = arguments[0];
        var url = (typeof input === "string") ? input :
                  (input && input.url) ? input.url : String(input);
        var init = arguments[1] || {};
        var headers = {};
        var hsrc = init.headers || (input && input.headers);
        if (hsrc) {
          if (typeof hsrc.forEach === "function") hsrc.forEach(function (v, k) { headers[k] = v; });
          else if (typeof hsrc === "object") Object.keys(hsrc).forEach(function (k) { headers[k] = hsrc[k]; });
        }
        if (/jioaicloud\.com/i.test(url)) record(headers);
      } catch (e) {}
      return origFetch.apply(this, arguments);
    };
  }

  // ---- Strategy B: wrap XMLHttpRequest ------------------------------------
  var origOpen = XMLHttpRequest.prototype.open,
      origSet = XMLHttpRequest.prototype.setRequestHeader,
      origSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u) {
    this.__jc_url = u; this.__jc_headers = {};
    return origOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.setRequestHeader = function (n, v) {
    try {
      if (this.__jc_headers && /jioaicloud\.com/i.test(this.__jc_url || "")) {
        this.__jc_headers[n] = v;
      }
    } catch (e) {}
    return origSet.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function () {
    try {
      if (/jioaicloud\.com/i.test(this.__jc_url || "")) record(this.__jc_headers);
    } catch (e) {}
    return origSend.apply(this, arguments);
  };

  // ---- Report --------------------------------------------------------------
  function report() {
    var auth = FOUND["authorization"];
    if (!/^basic\s/i.test(auth)) auth = "Basic " + auth;
    var cfg = { auth_token: auth, user_id: FOUND["x-user-id"], device_key: FOUND["x-device-key"] };

    setToast("<div style='font-weight:bold'>\u2713 Credentials captured!</div>" +
      "<div style='margin-top:6px;white-space:pre-wrap'>" +
      "auth_token: " + auth.slice(0, 12) + "...(truncated)\n" +
      "user_id: " + cfg.user_id + "\n" +
      "device_key: " + cfg.device_key + "</div>" +
      "<div style='margin-top:6px'>Full config.json printed in the Console.</div>");
    setTimeout(restore, 60000); // leave the green toast readable

    console.log("%c========== Jio AI Cloud credentials captured ========== ",
                "color:#fff;background:#0a7d32;font-weight:bold;padding:2px 6px");
    console.log(JSON.stringify(cfg, null, 2));
    console.log("%c Copy the object above into config.json, or re-run:  " +
                "python examples/setup_credentials.py   and paste the three values.",
                "color:#0a7d32;font-weight:bold");
    console.log("Requests inspected:", CAPTURED_URLS);
  }

  function restore() {
    try {
      if (origFetch) window.fetch = origFetch;
      XMLHttpRequest.prototype.open = origOpen;
      XMLHttpRequest.prototype.setRequestHeader = origSet;
      XMLHttpRequest.prototype.send = origSend;
    } catch (e) {}
  }

  // ---- Kick off -------------------------------------------------------------
  toastState();
  console.log("%c[Jio extractor v2] Watching *.jioaicloud.com requests. " +
              "Click around INSIDE the app now - do NOT reload (F5).",
              "color:#e80;font-weight:bold");

  setTimeout(function () {
    if (DONE) return;
    restore();
    if (Object.keys(FOUND).length > 0) {
      setToast("<div style='font-weight:bold'>Partial capture after 30s</div>" +
        "<div>Got " + NEEDED.filter(function (h){return FOUND[h];}).length +
        "/3. Keep clicking around, or re-paste the script to continue.</div>");
    } else {
      setToast("<div style='font-weight:bold'>No jioaicloud requests seen in 30s.</div>" +
        "<div>Use the cURL method instead:<br>Network tab &rarr; click any " +
        "jioaicloud.com request &rarr; right-click &rarr; Copy &rarr; Copy as cURL," +
        "<br>then run:<br><b>python examples/setup_credentials.py --from-curl</b></div>");
    }
  }, 30000);
})();
