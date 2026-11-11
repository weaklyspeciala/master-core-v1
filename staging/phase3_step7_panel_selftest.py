import ast, hashlib, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
integration = root / "MASTER_CORE_V1" / "integration"
panel_file = integration / "approval_panel.py"
bridge_file = integration / "workstation_safety_bridge.py"
expected_old_bridge = sys.argv[2].lower()
ast.parse(panel_file.read_text(encoding="utf-8"), filename=str(panel_file))
ast.parse(bridge_file.read_text(encoding="utf-8"), filename=str(bridge_file))
sys.path.insert(0, str(integration))
from approval_panel import render_panel
html = render_panel()
tests = {
    "Panel renders standalone HTML": html.lstrip().lower().startswith("<!doctype html>"),
    "Panel uses local safety API": "/api/safety/pending" in html and "/api/safety/approve" in html,
    "Proposed content is inserted safely": "textContent" in html and "proposed_content" in html,
    "Exact APPROVE confirmation is required": 'typed!=="APPROVE"' in html,
    "Test-sandbox tickets cannot be approved": "approval disabled" in html.lower() and "isTestTicket" in html,
    "Expired tickets cannot be approved": "isExpired" in html and "approve.disabled=sandbox||expired" in html,
    "Reject endpoint is available": "/api/safety/reject" in html,
    "Ticket details endpoint is used": "/api/safety/ticket?" in html,
    "No external script or stylesheet dependencies": "https://" not in html and "http://" not in html,
    "Bridge includes /safety page route": 'parsed.path == "/safety"' in bridge_file.read_text(encoding="utf-8"),
    "Bridge was changed from inspected Step 6 hash": hashlib.sha256(bridge_file.read_bytes()).hexdigest() != expected_old_bridge,
}
for name, ok in tests.items():
    if not ok:
        raise AssertionError("FAIL: " + name)
    print("PASS | " + name)
print(f"\nSTEP7_PANEL_SELFTEST_RESULT=PASS\nSTEP7_PANEL_CHECKS={len(tests)}")