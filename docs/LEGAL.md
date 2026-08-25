# LEGAL.md — Legal & Compliance Notes

> **Note:** This project targets an UNSTABLE, unofficial API. Last verified against production: 2026-08-25 (26/26 checks). Endpoints can break at any time — see KNOWN_ISSUES.md.

This document summarizes the legal posture of the **Unofficial Jio AI Cloud
Python SDK & CLI** project. It is informational, not legal advice.

---

## 1. Project Identity & Trademark Attribution

| Item | Statement |
|---|---|
| Status | Independent, unofficial, community-developed software |
| Relationship to Jio | **None.** Not affiliated, associated, authorized, endorsed by, or officially connected with Reliance Jio Infocomm Ltd. ("Jio") or its subsidiaries |
| Trademarks | "Jio", "Jio AI Cloud", "JioCloud" and related marks belong to their respective owners |
| Mark usage | Nominative fair use only — to identify the service this tool interoperates with |

## 2. Purpose Clause (Fair-Use / Interoperability)

The sole intended purposes of this software are:

1. **Personal data portability** for the account owner (download, inventory,
   re-organize your own files);
2. **Personal backup / disaster recovery** of data you already own;
3. **Interoperability** with your own tooling via a documented client;
4. **Education and research** on cloud-storage client protocols.

It is explicitly **not** designed for, and must not be used for:
accessing other people's accounts, bulk scraping, circumventing paywalls or
quotas, redistributing copyrighted content, or any unlawful activity.

## 3. License

MIT License — see [LICENSE](https://github.com/Ns81000/jiocloud_client/blob/main/LICENSE). The license includes an additional
non-affiliation notice that forms part of the license text for this project.

## 4. Warranty Disclaimer & Limitation of Liability

THE SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND. To the
maximum extent permitted by law, the authors and contributors accept no
liability for:

- rate limits, throttling, account suspension, or other **account actions**
  by the service provider;
- **service changes** that break any feature without notice;
- **data loss** of any kind (always maintain independent backups);
- misuse, credential leakage caused by user error, or third-party claims.

Full text: [DISCLAIMER.md](DISCLAIMER.md), sections 3-4.

## 5. Data Privacy & Credential Handling

- Credentials live **only** in local `config.json` or `JIOCLOUD_*`
  environment variables on the user's machine.
- The SDK performs **zero telemetry**. The only network destinations are
  official `*.jioaicloud.com` endpoints over TLS.
- Example files, docs, and templates in this repository contain
  **placeholders only** — never real credentials.
- Recommended handling: set restrictive file permissions on `config.json`,
  add it to `.gitignore`, rotate sessions periodically, and never paste
  tokens into issue trackers or chat logs.

## 6. Reverse-Engineering & Interoperability Notice

Protocol details in this project were derived from observing network traffic
of the author's own authenticated sessions (a standard technique for
building interoperable clients) and from publicly served web assets. No
proprietary source code, no DRM circumvention, and no access-control bypass
is involved: every request uses the same authenticated session credentials
the legitimate web client itself uses, on behalf of the same account owner.

## 7. Takedown / Contact

If you are a rights holder (including a representative of Reliance Jio
Infocomm Limited) and believe any content here infringes your rights, open
an issue in this project's repository and we will promptly review and, where
appropriate, remove or amend the material.
