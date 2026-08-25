# Unit tests for parse_curl: all Chrome dialects incl. the real Windows CMD
# output that failed in the field. No live network calls, no secrets printed.
import sys

src = open("examples/setup_credentials.py", encoding="utf-8").read()
ns = {"__file__": "examples/setup_credentials.py"}
exec(compile(src.split("def main()")[0], "setup_credentials", "exec"), ns)
parse_curl = ns["parse_curl"]

FAKE_TOK = ("Basic OTZlZjA3YjA3YjgyNDI4NmFhZDQzOGQyNTg3MDcxMWMjQVRLQSM2R3liL0p4TGZSWWJI"
            "QXlFa2tDUkJiWlluK1ZIK1FwQ2hIWDRxSlZUemxXMlNkZGgzRzVJVUhjU3BGZlVvSFVpRlZhNC85"
            "ZVhudEZValdWRms5VktDZUZJd2xzajlPTVQya0IwSXR5dkd2WC9uNXQ3UHZkQlBleXBpR3MycjhY")
EXPECTED = {"auth_token": FAKE_TOK,
            "user_id": "bbaac1b819b3486eab69032703b7f0ed",
            "device_key": "7ad47542-f82f-44db-95a9-de2a0f812413"}

# 1. The EXACT Windows CMD shape from the field report (caret escapes).
cmd_real = '''curl ^"https://api.jioaicloud.com/security/users^" ^
  -H ^"Accept: application/json; charset=UTF-8^" ^
  -H ^"Accept-Language: en-US,en;q=0.9^" ^
  -H ^"Authorization: Basic OTZlZjA3YjA3YjgyNDI4NmFhZDQzOGQyNTg3MDcxMWMjQVRLQSM2R3liL0p4TGZSWWJIQXlFa2tDUkJiWlluK1ZIK1FwQ2hIWDRxSlZUemxXMlNkZGgzRzVJVUhjU3BGZlVvSFVpRlZhNC85ZVhudEZValdWRms5VktDZUZJd2xzajlPTVQya0IwSXR5dkd2WC9uNXQ3UHZkQlBleXBpR3MycjhY^" ^
  -H ^"Connection: keep-alive^" ^
  -H ^"Content-Type: application/json; charset=UTF-8^" ^
  -H ^"Origin: https://www.jioaicloud.com^" ^
  -H ^"Referer: https://www.jioaicloud.com/^" ^
  -H ^"Sec-Fetch-Dest: empty^" ^
  -H ^"Sec-Fetch-Mode: cors^" ^
  -H ^"Sec-Fetch-Site: same-site^" ^
  -H ^"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36^" ^
  -H ^"X-Api-Key: c153b48e-d8a1-48a0-a40d-293f1dc5be0e^" ^
  -H ^"X-App-Secret: ODc0MDE2M2EtNGY0MC00YmU2LTgwZDUtYjNlZjIxZGRkZjlj^" ^
  -H ^"X-Client-Details: clientType:WEB; appVersion:86.0.1^" ^
  -H ^"X-Device-Key: 7ad47542-f82f-44db-95a9-de2a0f812413^" ^
  -H ^"X-Device-Type: W^" ^
  -H ^"X-User-Id: bbaac1b819b3486eab69032703b7f0ed^" ^
  -H ^"sec-ch-ua: ^\\^"Google Chrome^\\^";v=^\\^"147^\\^", ^\\^"Not.A/Brand^\\^";v=^\\^"8^\\^"^" ^
  -H ^"sec-ch-ua-mobile: ?0^" ^
  -H ^"sec-ch-ua-platform: ^\\^"Windows^\\^"^"'''
v = parse_curl(cmd_real)
assert v == EXPECTED, ("CMD-real failed", v)
print("real CMD caret dialect -> OK")

# 2. POSIX bash copy with $'\r' carriage returns.
posix_cr = """curl 'https://api.jioaicloud.com/security/users' \\
  -H $'Authorization: Basic OTZlZjA3...==\\r' \\
  -H $'X-User-Id: bbaac1b819b3486eab69032703b7f0ed\\r' \\
  -H $'X-Device-Key: 7ad47542-f82f-44db-95a9-de2a0f812413\\r'"""
v = parse_curl(posix_cr)
assert v["user_id"] == "bbaac1b819b3486eab69032703b7f0ed", v
assert v["device_key"] == "7ad47542-f82f-44db-95a9-de2a0f812413", v
assert v["auth_token"] == "Basic OTZlZjA3...==", v
print("POSIX $'\\r' dialect -> OK")

# 3. Plain single-line double-quoted (older Chrome / wget format).
simple = ('curl "https://api.jioaicloud.com/security/users" '
          '-H "Authorization: Basic abc==" '
          '-H "X-User-Id: u32chars00000000000000000000000" '
          '-H "X-Device-Key: dddddddd-eeee-4fff-8000-111122223333"')
v = parse_curl(simple)
assert v == {"auth_token": "Basic abc==",
             "user_id": "u32chars00000000000000000000000",
             "device_key": "dddddddd-eeee-4fff-8000-111122223333"}, v
print("plain double-quote one-liner -> OK")

# 4. Empty input.
assert parse_curl("curl 'https://example.com'") == {}
print("no headers -> {} OK")

print("ALL parse_curl TESTS PASS")
