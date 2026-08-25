/**
 * Jio AI Cloud — one-paste credential extractor v3 (Chrome DevTools Console)
 *
 * HOW TO USE
 * 1. Log in to https://www.jioaicloud.com in Chrome.
 * 2. Press F12, open the Console tab. Make sure the context dropdown at the
 *    top of the console says "top" (not an iframe).
 * 3. Paste this ENTIRE file and press Enter. A pink toast appears top-right.
 * 4. IMPORTANT: do NOT reload the page (F5 wipes the watcher). Instead click
 *    around INSIDE the app: open My Files, Photos, open then close a file.
 * 5. When all three values are found, the toast turns green showing the
 *    values plus a "Copy config.json" button. Clicking it puts the full JSON
 *    on your clipboard. The full JSON is also printed in this Console.
 *
 * How it works: window.fetch and XMLHttpRequest are wrapped BEFORE requests
 * fire; request headers of *.jioaicloud.com calls are inspected. Originals
 * are restored afterwards. Nothing is transmitted anywhere by this script.
 *
 * The overlay self-heals: if the app's framework wipes stray nodes from
 * <body> (SPAs do this on route re-renders), a watchdog re-creates it.
 *
 * If nothing is captured within 30s, use the cURL method instead:
 * DevTools Network tab -> filter: domain:api.jioaicloud.com security/users -method:OPTIONS
 * -> click the GET request -> Copy as cURL ->
 *    python examples/setup_credentials.py --from-curl
 */
(function () {
  "use strict";

  var FOUND = {};
  var CAPTURED_URLS = 0;
  var NEEDED = ["authorization", "x-user-id", "x-device-key"];
  var DONE = false;
  var CAPTURED_CFG = null;

  var TOAST_ID = "__jc_toast";
  var TOAST_CSS = "position:fixed;top:14px;right:14px;z-index:2147483647;" +
    "background:#b3266e;color:#fff;padding:12px 16px;border-radius:10px;" +
    "font:13px/1.45 monospace;max-width:420px;box-shadow:0 4px 18px rgba(0,0,0,.4);";

  // ---- Self-healing toast --------------------------------------------------
  // The host SPA may remove unknown <body> children during route re-renders;
  // a watchdog repaints the toast from UI_STATE whenever it vanishes.
  var UI_STATE = "watching"; // watching | captured | partial | timeout
  function paint(html, wire) {
    var t = document.getElementById(TOAST_ID);
    if (!t) {
      t = document.createElement("div");
      t.id = TOAST_ID;
      t.style.cssText = TOAST_CSS;
      (document.body || document.documentElement).appendChild(t);
    }
    t.innerHTML = html;
    if (wire) wire(t);
    return t;
  }

  function paintWatching() {
    var have = NEEDED.filter(function (h) { return FOUND[h]; }).length;
    var rows = NEEDED.map(function (h) {
      var v = FOUND[h];
      return "<div>" + (v ? "\u2713" : "\u2022") + " " + h + ": <b>" +
        (v ? String(v).slice(0, 10) + "\u2026" : "waiting") + "</b></div>";
    }).join("");
    paint("<div style='font-weight:bold;margin-bottom:4px'>Jio extractor: " +
      have + "/3 captured \u2014 now CLICK AROUND the app (do NOT press F5)</div>" + rows);
  }

  function paintTimeout(msg) {
    paint("<div style='font-weight:bold'>" + msg + "</div>");
  }

  function paintCaptured(cfg) {
    var auth = cfg.auth_token;
    paint(
      "<div style='font-weight:bold'>\u2713 Credentials captured!</div>" +
      "<div style='margin-top:6px;white-space:pre-wrap'>" +
      "auth_token: " + auth.slice(0, 12) + "...(truncated)\n" +
      "user_id: " + cfg.user_id + "\n" +
      "device_key: " + cfg.device_key + "</div>" +
      "<button id='__jc_copy' style='margin-top:8px;padding:6px 14px;border:0;" +
      "border-radius:6px;background:#fff;color:#b3266e;font-weight:bold;" +
      "cursor:pointer'>Copy config.json</button>" +
      "<div id='__jc_copied' style='margin-top:4px;display:none'>Copied \u2713 " +
      "Paste into <b>config.json</b>, then run <b>python cli.py info</b> to verify.</div>",
      function (toastEl) {
        var btn = toastEl.querySelector("#__jc_copy");
        if (!btn) return;
        btn.addEventListener("click", function () {
          var json = JSON.stringify(cfg, null, 2);
          function done() {
            btn.style.background = "#0a7d32";
            btn.style.color = "#fff";
            btn.textContent = "Copied \u2713";
            var note = toastEl.querySelector("#__jc_copied");
            if (note) note.style.display = "block";
          }
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(json).then(done, done);
          } else {
            var ta = document.createElement("textarea");
            ta.value = json;
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand("copy"); } catch (e) {}
            document.body.removeChild(ta);
            done();
          }
        });
      });
  }

  var watchdogStart = Date.now();
  setInterval(function () {
    // Stop repainting 15 minutes after injection; by then the user is done
    // and we should not fight the app forever.
    if (Date.now() - watchdogStart > 15 * 60 * 1000) return;
    if (document.getElementById(TOAST_ID)) return;
    if (UI_STATE === "captured" && CAPTURED_CFG) paintCaptured(CAPTURED_CFG);
    else if (UI_STATE === "watching") paintWatching();
    else if (UI_STATE === "partial") paintTimeout(
      "<div style='font-weight:bold'>Partial capture</div><div>Got " +
      NEEDED.filter(function (h) { return FOUND[h]; }).length +
      "/3 - keep clicking around, or re-paste the script.</div>");
    else if (UI_STATE === "timeout") paintTimeout(
      "<div style='font-weight:bold'>No jioaicloud requests seen in 30s.</div>" +
      "<div>Use the cURL method:<br>Network tab &rarr; filter " +
      "<b>domain:api.jioaicloud.com security/users -method:OPTIONS</b>" +
      "<br>&rarr; click the GET request &rarr; Copy as cURL, then run:" +
      "<br><b>python examples/setup_credentials.py --from-curl</b></div>");
  }, 700);

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
    } else if (!DONE) {
      paintWatching();
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
    CAPTURED_CFG = {
      auth_token: auth,
      user_id: FOUND["x-user-id"],
      device_key: FOUND["x-device-key"]
    };
    UI_STATE = "captured";
    paintCaptured(CAPTURED_CFG);
    setTimeout(restore, 60000);

    console.log("%c========== Jio AI Cloud credentials captured ========== ",
                "color:#fff;background:#0a7d32;font-weight:bold;padding:2px 6px");
    console.log(JSON.stringify(CAPTURED_CFG, null, 2));
    console.log("%c Or click 'Copy config.json' on the page overlay, then paste " +
                "into config.json and verify with:  python cli.py info",
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
  paintWatching();
  console.log("%c[Jio extractor v3] Watching *.jioaicloud.com requests. " +
              "Click around INSIDE the app now - do NOT reload (F5).",
              "color:#e80;font-weight:bold");

  setTimeout(function () {
    if (DONE) return;
    restore();
    if (Object.keys(FOUND).length > 0) {
      UI_STATE = "partial";
      paintTimeout("");
    } else {
      UI_STATE = "timeout";
      paintTimeout("No jioaicloud requests seen in 30s.");
      console.warn("[Jio extractor] Nothing captured. Use the cURL method:");
      console.warn("  Network tab -> filter: domain:api.jioaicloud.com security/users -method:OPTIONS");
      console.warn("  -> click the GET request -> Copy as cURL");
      console.warn("  -> python examples/setup_credentials.py --from-curl");
    }
  }, 30000);
})();
