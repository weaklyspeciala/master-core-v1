import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

root = pathlib.Path(sys.argv[1]).resolve()
app_workspace = pathlib.Path(sys.argv[2]).resolve()
sandbox = app_workspace / "MASTER_CORE_V1_STEP6_LIVE_HTTP_SANDBOX_V2"
base = "http://127.0.0.1:8765"
origin = base
checks = []

def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"FAIL: {name}: {detail}")
    checks.append(name)
    print(f"PASS | {name}" + (f" | {detail}" if detail else ""))

def request(method, path, payload=None, request_origin=origin):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Origin": request_origin, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
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

# Verify live endpoint before creating test data.
status, body = request("GET", "/api/safety/pending")
check("Actual server responds to safety endpoint", status == 200 and body.get("ok") is True, f"HTTP {status}")

if sandbox.exists():
    raise RuntimeError(f"Refusing to overwrite existing V2 sandbox: {sandbox}")
sandbox.mkdir()

def rel(path):
    # API accepts paths relative to config.json's workspace="workspace".
    return path.resolve().relative_to(app_workspace).as_posix()

def post_write(path, content, request_origin=origin):
    return request("POST", "/api/write", {"path": rel(path), "content": content}, request_origin)

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
    check("Dashboard retrieves exact pending ticket", status == 200 and body.get("ok") is True, f"HTTP {status}")
    return body["ticket"]

def reject(ticket_id):
    return request("POST", "/api/safety/reject", {"ticket_id": ticket_id})

# Test 1: actual HTTP /api/write creates a ticket, no immediate write.
file_a = sandbox / "live_valid_text.txt"
original_a = b"LIVE ORIGINAL A\r\n"
file_a.write_bytes(original_a)
status_a, data_a = post_write(file_a, "LIVE APPROVED TEXT\n")
check("HTTP write returns pending approval", status_a == 202 and data_a.get("approval_required") is True,
      f"HTTP {status_a}; {data_a.get('error','')}")
check("HTTP write leaves file unchanged before approval", file_a.read_bytes() == original_a)
ticket_a = read_ticket(data_a["ticket_id"])

# Test 2: wrong confirmation is rejected.
status_wrong, _ = approve(ticket_a, typed="YES")
check("Wrong typed confirmation rejected", status_wrong == 400, f"HTTP {status_wrong}")
check("Wrong confirmation leaves original unchanged", file_a.read_bytes() == original_a)

# Test 3: correct exact-hash approval applies validated edit.
status_good, good_body = approve(ticket_a)
check("Correct hash-bound approval validates", status_good == 200 and good_body.get("status") == "validated",
      f"HTTP {status_good}; status={good_body.get('status')}")
check("Approved edit appears on disk", file_a.read_text(encoding="utf-8") == "LIVE APPROVED TEXT\n")
check("Approved edit has backup", pathlib.Path(good_body["backup"]).is_file())

# Test 4: foreign Origin is rejected.
file_b = sandbox / "live_origin_guard.txt"
original_b = b"LIVE ORIGINAL B\r\n"
file_b.write_bytes(original_b)
status_origin, _ = post_write(file_b, "NOT AUTHORIZED\n", "http://evil.example:8765")
check("Foreign Origin rejected", status_origin == 403, f"HTTP {status_origin}")
check("Foreign Origin leaves target unchanged", file_b.read_bytes() == original_b)

# Test 5: invalid JSON is ticketed and rolled back after explicit approval.
file_c = sandbox / "live_rollback.json"
original_c = b'{"safe": true}\r\n'
file_c.write_bytes(original_c)
status_c, data_c = post_write(file_c, '{"broken":')
check("Invalid JSON waits for approval", status_c == 202 and data_c.get("approval_required") is True,
      f"HTTP {status_c}")
check("Invalid JSON target unchanged before approval", file_c.read_bytes() == original_c)
ticket_c = read_ticket(data_c["ticket_id"])
status_rollback, rollback_body = approve(ticket_c)
check("Validation failure returns rolled_back",
      status_rollback == 422 and rollback_body.get("status") == "rolled_back",
      f"HTTP {status_rollback}; status={rollback_body.get('status')}")
check("HTTP rollback restores exact original bytes", file_c.read_bytes() == original_c)
check("Rollback backup remains available", pathlib.Path(rollback_body["backup"]).is_file())

# Test 6: wrong file hash rejects approval and does not write.
file_d = sandbox / "live_hash_guard.txt"
original_d = b"LIVE ORIGINAL D\r\n"
file_d.write_bytes(original_d)
status_d, data_d = post_write(file_d, "HASH GUARDED CONTENT\n")
check("Hash-guard fixture is pending", status_d == 202)
ticket_d = read_ticket(data_d["ticket_id"])
status_hash, _ = approve(ticket_d, current="0" * 64)
check("Mismatched current hash rejected", status_hash == 409, f"HTTP {status_hash}")
check("Hash mismatch leaves target unchanged", file_d.read_bytes() == original_d)

# Verify pending-list route and then reject the intentional leftover hash-guard ticket.
status_list, list_body = request("GET", "/api/safety/pending")
pending_ids = {x.get("ticket_id") for x in list_body.get("tickets", [])}
check("Pending list contains outstanding hash-guard ticket",
      status_list == 200 and data_d["ticket_id"] in pending_ids)

reject_status, reject_body = reject(data_d["ticket_id"])
check("Diagnostic hash-guard ticket cleaned up by rejection",
      reject_status == 200 and reject_body.get("status") == "rejected", f"HTTP {reject_status}")

print("\nSTEP6_LIVE_HTTP_RESULT=PASS")
print(f"STEP6_LIVE_HTTP_CHECKS={len(checks)}")
print(f"LIVE_TEST_SANDBOX={sandbox}")
print(f"APPROVED_BACKUP={good_body['backup']}")
print(f"ROLLBACK_BACKUP={rollback_body['backup']}")