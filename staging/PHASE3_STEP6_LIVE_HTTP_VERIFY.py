import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

workspace = pathlib.Path(sys.argv[1]).resolve()
sandbox = workspace / "MASTER_CORE_V1_STEP6_LIVE_HTTP_SANDBOX"
base = "http://127.0.0.1:8765"
origin = base
checks = []

def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"FAIL: {name}: {detail}")
    checks.append(name)
    print(f"PASS | {name}" + (f" | {detail}" if detail else ""))

def request(method, path, payload=None, request_origin=origin):
    url = base + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Origin": request_origin, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            raw = response.read()
            return response.status, json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            body = {"raw": raw.decode("utf-8", "replace")}
        return exc.code, body

# First contact checks that the actual server is running and bridge is installed.
status, body = request("GET", "/api/safety/pending")
check("Actual workstation server responds to safety endpoint",
      status == 200 and body.get("ok") is True,
      f"HTTP {status}")
if sandbox.exists():
    raise RuntimeError(f"Refusing to overwrite existing test sandbox: {sandbox}")
sandbox.mkdir()

def rel(path):
    return path.resolve().relative_to(workspace).as_posix()

def post_write(path, content, request_origin=origin):
    return request("POST", "/api/write", {
        "path": rel(path),
        "content": content,
    }, request_origin)

def approve(ticket, typed="APPROVE", current=None, proposed=None):
    return request("POST", "/api/safety/approve", {
        "ticket_id": ticket["ticket_id"],
        "typed_confirmation": typed,
        "expected_current_sha256": ticket["current_sha256"] if current is None else current,
        "expected_proposed_sha256": ticket["proposed_sha256"] if proposed is None else proposed,
    })

def read_ticket(ticket_id):
    query = urllib.parse.urlencode({"ticket_id": ticket_id})
    status, body = request("GET", "/api/safety/ticket?" + query)
    check("Local dashboard can retrieve pending ticket details",
          status == 200 and body.get("ok") is True,
          f"HTTP {status}")
    return body["ticket"]

# Test 1: actual HTTP /api/write must create a pending ticket, not write immediately.
file_a = sandbox / "live_valid_text.txt"
original_a = b"LIVE ORIGINAL A\r\n"
file_a.write_bytes(original_a)
status_a, data_a = post_write(file_a, "LIVE APPROVED TEXT\n")
check("HTTP /api/write returns pending approval",
      status_a == 202 and data_a.get("approval_required") is True,
      f"HTTP {status_a}")
check("HTTP /api/write leaves target unchanged before approval",
      file_a.read_bytes() == original_a)

ticket_a = read_ticket(data_a["ticket_id"])
# Test 2: wrong typed confirmation is rejected without touching the file.
status_wrong, wrong_body = approve(ticket_a, typed="YES")
check("Wrong confirmation rejected by actual HTTP endpoint", status_wrong == 400)
check("Wrong confirmation leaves original file untouched", file_a.read_bytes() == original_a)

# Test 3: good approval validates and commits.
status_good, good_body = approve(ticket_a)
check("Correct hash-bound approval succeeds",
      status_good == 200 and good_body.get("status") == "validated",
      f"HTTP {status_good}; status={good_body.get('status')}")
check("Approved file content appears on disk",
      file_a.read_text(encoding="utf-8") == "LIVE APPROVED TEXT\n")
check("Approved file has verified backup",
      pathlib.Path(good_body["backup"]).is_file())

# Test 4: foreign Origin rejected by actual HTTP endpoint.
file_b = sandbox / "live_origin_guard.txt"
original_b = b"LIVE ORIGINAL B\r\n"
file_b.write_bytes(original_b)
status_origin, origin_body = post_write(file_b, "NOT AUTHORIZED\n", "http://evil.example:8765")
check("Foreign Origin rejected by actual server", status_origin == 403, f"HTTP {status_origin}")
check("Foreign Origin attempt does not modify target", file_b.read_bytes() == original_b)

# Test 5: invalid JSON triggers real automatic rollback through HTTP approval.
file_c = sandbox / "live_rollback.json"
original_c = b'{"safe": true}\r\n'
file_c.write_bytes(original_c)
status_c, data_c = post_write(file_c, '{"broken":')
check("Invalid JSON edit waits for approval", status_c == 202 and data_c.get("approval_required") is True)
check("Invalid JSON target unchanged before approval", file_c.read_bytes() == original_c)
ticket_c = read_ticket(data_c["ticket_id"])
status_rollback, rollback_body = approve(ticket_c)
check("Validation failure returns rolled_back",
      status_rollback == 422 and rollback_body.get("status") == "rolled_back",
      f"HTTP {status_rollback}; status={rollback_body.get('status')}")
check("Real HTTP rollback restores exact original bytes", file_c.read_bytes() == original_c)
check("Rollback backup remains available",
      pathlib.Path(rollback_body["backup"]).is_file())

# Test 6: current/proposed hash mismatch is rejected.
file_d = sandbox / "live_hash_guard.txt"
original_d = b"LIVE ORIGINAL D\r\n"
file_d.write_bytes(original_d)
status_d, data_d = post_write(file_d, "HASH GUARDED CONTENT\n")
check("Hash-guard fixture enters pending state", status_d == 202)
ticket_d = read_ticket(data_d["ticket_id"])
status_hash, hash_body = approve(ticket_d, current="0" * 64)
check("Mismatched hash is rejected by real API", status_hash == 409)
check("Hash mismatch leaves target unchanged", file_d.read_bytes() == original_d)

# Pending API list must include a pending ticket from the hash-guard test.
status_list, list_body = request("GET", "/api/safety/pending")
pending_ids = {item.get("ticket_id") for item in list_body.get("tickets", [])}
check("Pending ticket list reflects outstanding review",
      status_list == 200 and data_d["ticket_id"] in pending_ids)

print("\nSTEP6_LIVE_HTTP_RESULT=PASS")
print(f"STEP6_LIVE_HTTP_CHECKS={len(checks)}")
print(f"LIVE_TEST_SANDBOX={sandbox}")
print(f"APPROVED_BACKUP={good_body['backup']}")
print(f"ROLLBACK_BACKUP={rollback_body['backup']}")