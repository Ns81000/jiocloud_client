# DISCLAIMER

## 1. Unofficial Project — No Affiliation, No Endorsement

This software (**Unofficial Jio AI Cloud Python SDK & CLI**) is an
**independent, community-developed, unofficial project**.

It is **not affiliated with, associated with, authorized by, endorsed by, or
in any way officially connected with Reliance Jio Infocomm Limited ("Jio")
or any of its subsidiaries, affiliates, or partners.**

- "Jio", "Jio AI Cloud", "JioCloud", and all related names, logos, and marks
  are **trademarks of their respective owners**.
- Any use of these marks in this project is purely **nominative and
  descriptive** — i.e., to identify the service this tool interoperates with —
  and does not imply sponsorship, endorsement, approval, or partnership of
  any kind.
- No official Jio documentation was provided for this project; the protocol
  knowledge here derives from observation of network traffic of the user's
  own sessions and from public information.

## 2. Personal Backup & Educational Use Only

This tool is created strictly for:

1. **Personal data portability** — accessing and downloading **your own**
   files from **your own** Jio AI Cloud account;
2. **Interoperability** — enabling your own automation and backup workflows;
3. **Educational purposes** — studying how cloud storage clients communicate,
   under fair-use guidelines.

You may **only** use it with credentials for an account you own or are
explicitly authorized to operate. Using it against accounts you do not
control is strictly prohibited and may be unlawful.

## 3. Use at Your Own Risk — "AS IS" Software

The software is provided **"AS IS", WITH ALL FAULTS**, without warranty of
any kind, express or implied, including but not limited to the warranties of
merchantability, fitness for a particular purpose, and non-infringement.

**You assume full responsibility for any use.** In particular, the authors
and contributors are **NOT liable** for:

- **Account actions**, including rate limiting, temporary blocks, suspension,
  or termination imposed by Jio as a result of automated access from this
  tool;
- **Service changes** — Jio may change, break, deprecate, or restrict its
  APIs at any time without notice, which can cause this tool to stop working
  entirely;
- **Data loss** — including accidental deletion, failed restores, overwrites,
  or incomplete backups. Always keep independent copies of important data;
- **Security incidents** arising from mishandling of your own credentials on
  your own machine;
- **Any direct, indirect, incidental, special, exemplary, or consequential
  damages** (including loss of data, profits, or goodwill) arising from the
  use of, or inability to use, this software.

## 4. Data Privacy & Credential Safety

- Your session token, user ID, device key, and any other credentials are
  stored **purely locally** in `config.json` (or environment variables) on
  your own computer.
- The SDK transmits credentials **only** to official `*.jioaicloud.com` API
  endpoints over TLS, and **never** to any third-party server, telemetry
  endpoint, or analytics provider controlled by this project.
- This project contains **no telemetry, tracking, or data collection**.
- You are responsible for protecting `config.json`: never commit it to
  source control, never share it, and revoke/re-login your web session if it
  leaks.

## 5. Rate Limiting & Fair Use Etiquette

The client deliberately includes throttling defaults (small page delays,
bounded worker counts). Even so, aggressive bulk operations may trigger
server-side rate limits. Be considerate: run large syncs off-peak, prefer
incremental backups, and respect any rate-limit responses (HTTP 429) the
service returns.

## 6. Compliance With Platform Terms Is Your Responsibility

Automated access to a cloud storage platform may be restricted or prohibited
by that platform's terms of service. Whether and how you may use this tool
against your own account depends on the agreement between **you** and
**Reliance Jio Infocomm Limited**. Nothing in this project constitutes legal
advice. If in doubt, do not use this tool.

---
*Last reviewed: 2026-08. If you are a representative of Reliance Jio
Infocomm Limited and believe any part of this project should be changed or
removed, please open an issue in this project's repository.*
