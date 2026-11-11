import json, pathlib, sys, urllib.error, urllib.parse, urllib.request

workspace = pathlib.Path(sys.argv[1]).resolve()
fixture = pathlib.Path(sys.argv[2]).resolve()
base = "http://127.0.0.1:8765"
origin = base

def send(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Origin": origin, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            raw = response.read()
            body = json.loads(raw.decode("utf-8")) if raw else {}
            return response.status, body
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            body = {"raw_response": raw.decode("utf-8", "replace")}
        return exc.code, body

before = fixture.read_bytes()
relative = fixture.relative_to(workspace).as_posix()

status, body = send("GET", "/api/safety/pending")
print(f"SAFETY_ENDPOINT_HTTP={status}")
print("SAFETY_ENDPOINT_BODY=" + json.dumps(body, ensure_ascii=False))

status, body = send("POST", "/api/write", {
    "path": relative,
    "content": "DIAGNOSTIC PROPOSAL - MUST NOT BE APPLIED\n",
})
print(f"WRITE_ENDPOINT_HTTP={status}")
print("WRITE_ENDPOINT_BODY=" + json.dumps(body, ensure_ascii=False, indent=2))

# If the route worked and created a ticket, reject it immediately.
ticket_id = body.get("ticket_id") if isinstance(body, dict) else None
if ticket_id:
    reject_status, reject_body = send("POST", "/api/safety/reject", {"ticket_id": ticket_id})
    print(f"DIAGNOSTIC_TICKET_REJECT_HTTP={reject_status}")
    print("DIAGNOSTIC_TICKET_REJECT_BODY=" + json.dumps(reject_body, ensure_ascii=False))

after = fixture.read_bytes()
print(f"FIXTURE_UNCHANGED={before == after}")
print(f"FIXTURE_SHA256_BEFORE={__import__('hashlib').sha256(before).hexdigest()}")
print(f"FIXTURE_SHA256_AFTER={__import__('hashlib').sha256(after).hexdigest()}")