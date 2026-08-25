# End-to-end clipboard flow test WITHOUT touching real config.json or network:
# put a fake cURL on the clipboard via PowerShell, then run the module's
# _read_clipboard + parse_curl exactly as main() would.
import subprocess
import sys

src = open("examples/setup_credentials.py", encoding="utf-8").read()
ns = {"__file__": "examples/setup_credentials.py"}
exec(compile(src.split("def main()")[0], "setup_credentials", "exec"), ns)

fake_curl = ('curl ^"https://api.jioaicloud.com/security/users^" ^\n'
             '  -H ^"Authorization: Basic FAKECLIPBOARDTOKEN==^" ^\n'
             '  -H ^"X-User-Id: feedfacefeedfacefeedfacefeedface^" ^\n'
             '  -H ^"X-Device-Key: 12345678-abcd-4ef0-9876-543210fedcba^" ^\n'
             '  -H ^"X-Device-Type: W^"')

# Put it on the clipboard via a temp file (avoids PowerShell arg-escaping)
import tempfile, os
tf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
tf.write(fake_curl); tf.close()
subprocess.run(["powershell", "-NoProfile", "-Command",
                "Get-Content -Raw -LiteralPath '" + tf.name.replace("'", "''") +
                "' | Set-Clipboard"], check=True, timeout=15)
os.unlink(tf.name)

got = ns["_read_clipboard"]()
assert "FAKECLIPBOARDTOKEN" in got, f"clipboard read failed: {got!r}"
vals = ns["parse_curl"](got)
print("clipboard -> parsed:", {k: v[:20] + ("..." if len(v) > 20 else "")
                               for k, v in vals.items()})
assert vals["auth_token"] == "Basic FAKECLIPBOARDTOKEN=="
assert vals["user_id"] == "feedfacefeedfacefeedfacefeedface"
assert vals["device_key"] == "12345678-abcd-4ef0-9876-543210fedcba"
print("CLIPBOARD FLOW OK")
