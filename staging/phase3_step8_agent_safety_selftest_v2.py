import hashlib
import json
import pathlib
import sys
import time

root = pathlib.Path(sys.argv[1]).resolve()
sandbox = root / "workspace" / "MASTER_CORE_V1_STEP8_AGENT_SANDBOX_V2"
integration = root / "MASTER_CORE_V1" / "integration"
safety = root / "MASTER_CORE_V1" / "safety"
sys.path.insert(0, str(integration))
sys.path.insert(0, str(safety))
import agent_safety_adapter_v2 as agent
import safe_file_ops as sfo

checks = []
def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"FAIL: {name}: {detail}")
    checks.append(name)
    print(f"PASS | {name}" + (f" | {detail}" if detail else ""))

def sha(data):
    return hashlib.sha256(data).hexdigest()

sandbox.mkdir(parents=False, exist_ok=False)
project = (root / "workspace").resolve()
check("Configured multi-root list includes workspace", project in agent._configured_roots())
stickman = pathlib.Path(r"H:\LOCAL_CARTOON_STUDIO\stickman-video-director-AUTOPILOT-DEV").resolve()
check("Configured multi-root list includes Stickman repository", stickman in agent._configured_roots())

# A: pending edit does not modify the existing target.
file_a = sandbox / "agent_existing.txt"
original_a = b"AGENT ORIGINAL A\r\n"
file_a.write_bytes(original_a)
ticket_a = agent.create_agent_ticket(file_a, project, "MASTER_CORE_V1_STEP8_AGENT_SANDBOX_V2/agent_existing.txt", "AGENT PROPOSAL A\n")
check("Agent ticket is pending", ticket_a.get("status") == "pending")
check("Agent ticket is correctly typed", ticket_a.get("ticket_kind") == "agent_project_edit")
check("Pending Agent proposal does not change file", file_a.read_bytes() == original_a)

# B: incorrect hash is rejected without changing file.
try:
    agent.approve_agent_ticket(ticket_a["ticket_id"], "APPROVE", "0" * 64, ticket_a["proposed_sha256"])
    raise AssertionError("Incorrect current hash was unexpectedly accepted.")
except agent.AgentSafetyError as exc:
    check("Incorrect Agent current hash rejected", "SHA256" in str(exc))

check("Hash rejection leaves original bytes unchanged", file_a.read_bytes() == original_a)

# C: reject ticket and prevent replay.
ticket_path_a = sfo.APPROVAL_ROOT / (ticket_a["ticket_id"] + ".json")
ticket_data_a = json.loads(ticket_path_a.read_text(encoding="utf-8"))
ticket_data_a["status"] = "rejected"
ticket_data_a["proposed_content"] = ""
ticket_path_a.write_text(json.dumps(ticket_data_a, indent=2), encoding="utf-8")
try:
    agent.approve_agent_ticket(ticket_a["ticket_id"], "APPROVE", ticket_a["current_sha256"], ticket_a["proposed_sha256"])
    raise AssertionError("Rejected Agent ticket was replayed.")
except agent.AgentSafetyError:
    check("Rejected Agent ticket cannot be replayed", True)

# D: normal approved edit creates verified backup and applies content.
file_b = sandbox / "agent_success.txt"
original_b = b"AGENT ORIGINAL B\r\n"
file_b.write_bytes(original_b)
ticket_b = agent.create_agent_ticket(file_b, project, "MASTER_CORE_V1_STEP8_AGENT_SANDBOX_V2/agent_success.txt", "AGENT APPROVED B\n")
result_b = agent.approve_agent_ticket(ticket_b["ticket_id"], "APPROVE", ticket_b["current_sha256"], ticket_b["proposed_sha256"])
check("Approved Agent edit validates", result_b.get("status") == "validated")
check("Approved Agent content reaches target", file_b.read_text(encoding="utf-8") == "AGENT APPROVED B\n")
backup_b = pathlib.Path(result_b["backup"])
check("Agent backup exists", backup_b.is_file())
check("Agent backup exact bytes verified", backup_b.read_bytes() == original_b)
check("Agent backup SHA256 matches original", sha(backup_b.read_bytes()) == sha(original_b))

# E: invalid JSON is rolled back to exact bytes.
file_c = sandbox / "agent_invalid.json"
original_c = b'{"safe": true}\r\n'
file_c.write_bytes(original_c)
ticket_c = agent.create_agent_ticket(file_c, project, "MASTER_CORE_V1_STEP8_AGENT_SANDBOX_V2/agent_invalid.json", '{"broken":')
result_c = agent.approve_agent_ticket(ticket_c["ticket_id"], "APPROVE", ticket_c["current_sha256"], ticket_c["proposed_sha256"])
check("Invalid JSON triggers Agent rollback", result_c.get("status") == "rolled_back")
check("Agent rollback restores exact original bytes", file_c.read_bytes() == original_c)
check("Agent rollback backup retained", pathlib.Path(result_c["backup"]).is_file())

# F: new file ticket uses exclusive creation and approval.
file_d = sandbox / "agent_new_file.txt"
ticket_d = agent.create_agent_ticket(file_d, project, "MASTER_CORE_V1_STEP8_AGENT_SANDBOX_V2/agent_new_file.txt", "NEW APPROVED FILE\n")
check("New-file proposal leaves target absent", not file_d.exists())
result_d = agent.approve_agent_ticket(ticket_d["ticket_id"], "APPROVE", ticket_d["current_sha256"], ticket_d["proposed_sha256"])
check("Approved new file is created", result_d.get("status") == "validated" and file_d.is_file())
check("Approved new file content exact", file_d.read_text(encoding="utf-8") == "NEW APPROVED FILE\n")
check("New file has no fabricated pre-existing backup", result_d.get("backup") is None)

# G: new file validation failure removes only the exact file created by this ticket.
file_e = sandbox / "agent_new_invalid.json"
ticket_e = agent.create_agent_ticket(file_e, project, "MASTER_CORE_V1_STEP8_AGENT_SANDBOX_V2/agent_new_invalid.json", '{"bad":')
result_e = agent.approve_agent_ticket(ticket_e["ticket_id"], "APPROVE", ticket_e["current_sha256"], ticket_e["proposed_sha256"])
check("Invalid new file returns rolled_back", result_e.get("status") == "rolled_back")
check("Invalid new file cleanup removes only created test target", not file_e.exists())

# H: path outside configured trusted roots is refused.
outside = root.parent / "MASTER_AI_OUTSIDE_STEP8_TEST.txt"
try:
    agent.create_agent_ticket(outside, project, "../MASTER_AI_OUTSIDE_STEP8_TEST.txt", "blocked")
    raise AssertionError("Outside path was unexpectedly ticketed.")
except agent.AgentSafetyError:
    check("Outside trusted root refused", True)
check("No outside test file created", not outside.exists())

# I: install() must replace the Agent's direct write function with a proposal-only wrapper.
file_g = sandbox / "agent_tool_wrapper.txt"
original_g = b"AGENT WRAPPER ORIGINAL\\r\\n"
file_g.write_bytes(original_g)
namespace = {
    "tool_write": lambda args, project: {"ok": True, "unexpected_direct_write": True},
    "safe_file": lambda selected, relative: (pathlib.Path(selected) / relative).resolve(),
    "display_path": lambda target, selected: target.resolve().relative_to(pathlib.Path(selected).resolve()).as_posix(),
    "CFG": {"max_file_bytes": 100000},
    "ROOT": root,
}
agent.install(namespace)
wrapped = namespace["tool_write"](
    {"path": "MASTER_CORE_V1_STEP8_AGENT_SANDBOX_V2/agent_tool_wrapper.txt", "content": "WRAPPER PROPOSAL\\n"},
    root / "workspace",
)
check("Agent install replaces direct write with approval wrapper", namespace.get("_MASTER_AGENT_SAFETY_INSTALLED") is True)
check("Agent write wrapper returns pending approval", wrapped.get("status") == "pending_approval")
check("Agent write wrapper does not modify the target", file_g.read_bytes() == original_g)
sfo.reject_approval(wrapped["ticket_id"])
check("Agent wrapper test ticket rejected after test", True)

# J: startup bootstrap and pause-on-pending are present in patched Agent source.
patched_agent_text = (root / "autonomous_agent.py").read_text(encoding="utf-8-sig")
check("Agent startup installs safety adapter", "_p3_agent_safety.install(globals())" in patched_agent_text)
check("Agent task loop pauses for pending approval", 'result.get("status") == "pending_approval"' in patched_agent_text)

# K: approval server dispatches Agent-project tickets.
patched_bridge_text = (root / "MASTER_CORE_V1" / "integration" / "workstation_safety_bridge.py").read_text(encoding="utf-8-sig")
check("Approval bridge dispatches Agent-project tickets", 'ticket.get("ticket_kind") == "agent_project_edit"' in patched_bridge_text)

# L: expiry check.
file_f = sandbox / "agent_expired.txt"
file_f.write_bytes(b"EXPIRY ORIGINAL\n")
ticket_f = agent.create_agent_ticket(file_f, project, "MASTER_CORE_V1_STEP8_AGENT_SANDBOX_V2/agent_expired.txt", "EXPIRED CHANGE\n")
path_f = sfo.APPROVAL_ROOT / (ticket_f["ticket_id"] + ".json")
data_f = json.loads(path_f.read_text(encoding="utf-8"))
data_f["expires_at"] = time.time() - 1
path_f.write_text(json.dumps(data_f, indent=2), encoding="utf-8")
try:
    agent.approve_agent_ticket(ticket_f["ticket_id"], "APPROVE", ticket_f["current_sha256"], ticket_f["proposed_sha256"])
    raise AssertionError("Expired ticket was unexpectedly accepted.")
except agent.AgentSafetyError as exc:
    check("Expired Agent ticket rejected", "expired" in str(exc).lower())
check("Expired ticket leaves file unchanged", file_f.read_bytes() == b"EXPIRY ORIGINAL\n")

log = (root / "MASTER_CORE_V1" / "logs" / "agent_safety_audit.jsonl").read_text(encoding="utf-8")
check("Agent safety audit records ticket creation", "agent_approval_ticket_created" in log)
check("Agent safety audit records successful edit", "agent_project_edit_applied" in log)
check("Agent safety audit records rollback", "agent_automatic_rollback_completed" in log)
print(f"\nSTEP8_AGENT_SAFETY_RESULT=PASS\nSTEP8_AGENT_SAFETY_CHECKS={len(checks)}")
print(f"STEP8_TEST_SANDBOX={sandbox}")
print(f"AGENT_SAFETY_AUDIT={root / 'MASTER_CORE_V1' / 'logs' / 'agent_safety_audit.jsonl'}")