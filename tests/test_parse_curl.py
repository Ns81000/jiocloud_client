# Unit-test parse_curl against all Chrome cURL variants (no live calls).
import sys

src = open("examples/setup_credentials.py", encoding="utf-8").read()
ns = {"__file__": "examples/setup_credentials.py"}
exec(compile(src.split("def main()")[0], "setup_credentials", "exec"), ns)
parse_curl = ns["parse_curl"]

posix = r"""curl 'https://api.jioaicloud.com/security/users' \
  -H 'Authorization: Basic abcDEF123xyz==' \
  -H 'X-User-Id: deadbeefdeadbeefdeadbeefdeadbeef' \
  -H 'X-Device-Key: 12345678-90ab-4cde-8f01-234567890abc' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  --compressed"""
cmd = """curl "https://api.jioaicloud.com/security/users" ^
  -H "Authorization: Basic abcDEF123xyz==" ^
  -H "X-User-Id: deadbeefdeadbeefdeadbeefdeadbeef" ^
  -H "X-Device-Key: 12345678-90ab-4cde-8f01-234567890abc\""""

for name, sample in [("POSIX", posix), ("CMD", cmd)]:
    v = parse_curl(sample)
    assert v == {"auth_token": "Basic abcDEF123xyz==",
                 "user_id": "deadbeefdeadbeefdeadbeefdeadbeef",
                 "device_key": "12345678-90ab-4cde-8f01-234567890abc"}, (name, v)
    print(name, "-> OK")

v = parse_curl(r"""curl 'https://x.jioaicloud.com/y' -H 'authorization: RAWTOKEN99' -H 'X-USER-ID: u1' -H 'x-device-key: d1'""")
assert v["auth_token"] == "RAWTOKEN99" and v["user_id"] == "u1" and v["device_key"] == "d1"
print("raw token / mixed case -> OK")

assert parse_curl("curl 'https://example.com'") == {}
print("no-header input -> {} OK")
print("ALL parse_curl TESTS PASS")
