import ast, hashlib, json, os, pathlib, shutil, sys, time

agent = pathlib.Path(sys.argv[1]).resolve()
bridge = pathlib.Path(sys.argv[2]).resolve()
core = pathlib.Path(sys.argv[3]).resolve()
expected_agent = sys.argv[4].lower()
expected_bridge = sys.argv[5].lower()
backup_root = core / "backups"
logs = core / "logs"

def sha(data):
    return hashlib.sha256(data).hexdigest()

agent_raw = agent.read_bytes()
bridge_raw = bridge.read_bytes()
if sha(agent_raw) != expected_agent:
    raise SystemExit(f"Agent SHA256 mismatch: expected {expected_agent}, found {sha(agent_raw)}")
if sha(bridge_raw) != expected_bridge:
    raise SystemExit(f"Bridge SHA256 mismatch: expected {expected_bridge}, found {sha(bridge_raw)}")

agent_bom = agent_raw.startswith(b"\xef\xbb\xbf")
bridge_bom = bridge_raw.startswith(b"\xef\xbb\xbf")
agent_text = agent_raw.decode("utf-8-sig")
bridge_text = bridge_raw.decode("utf-8-sig")
agent_newline = "\r\n" if b"\r\n" in agent_raw else "\n"
bridge_newline = "\r\n" if b"\r\n" in bridge_raw else "\n"
agent_normal = agent_text.replace("\r\n", "\n").replace("\r", "\n")
bridge_normal = bridge_text.replace("\r\n", "\n").replace("\r", "\n")
agent_tree = ast.parse(agent_normal, filename=str(agent))
ast.parse(bridge_normal, filename=str(bridge))

if "_p3_agent_safety.install(globals())" in agent_normal:
    raise SystemExit("Agent safety bootstrap already exists.")
if "ticket.get(\"ticket_kind\") == \"agent_project_edit\"" in bridge_normal:
    raise SystemExit("Bridge Agent-ticket handler already exists.")

# Patch autonomous_agent.main() by inserting bootstrap at its first body line.
main_nodes = [n for n in agent_tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"]
if len(main_nodes) != 1:
    raise SystemExit(f"Expected one top-level main() function; found {len(main_nodes)}.")
main_node = main_nodes[0]
agent_lines = agent_normal.splitlines()
bootstrap = [
    "    _p3_agent_integration = ROOT / \"MASTER_CORE_V1\" / \"integration\"",
    "    if not _p3_agent_integration.is_dir():",
    "        raise RuntimeError(\"MASTER_CORE_V1 Agent safety integration is missing; refusing to run without approval protection.\")",
    "    if str(_p3_agent_integration) not in sys.path:",
    "        sys.path.insert(0, str(_p3_agent_integration))",
    "    import agent_safety_adapter_v2 as _p3_agent_safety",
    "    _p3_agent_safety.install(globals())",
]
agent_insert_at = main_node.lineno  # zero-based insertion immediately after def main():
agent_lines[agent_insert_at:agent_insert_at] = bootstrap
patched_agent = "\n".join(agent_lines) + ("\n" if agent_normal.endswith("\n") else "")

# Pause the model loop immediately after an Agent write becomes pending approval.
needle = '            history.append({"tool": name, "args": args, "result": result})'
if patched_agent.count(needle) != 1:
    raise SystemExit(f"Expected exactly one Agent history append anchor; found {patched_agent.count(needle)}.")
pause = "\n".join([
    needle,
    '            if result.get("status") == "pending_approval":',
    '                return ("A project file change is waiting for your review in the Safety Approval Center. No project file has been changed yet. Approve or reject the ticket, then submit the next task."), history',
])
patched_agent = patched_agent.replace(needle, pause, 1)
ast.parse(patched_agent, filename=str(agent))

# Extend Step 7 bridge's approval route to dispatch Agent-project tickets.
bridge_anchor = "\n".join([
    "            result = recovery.approve_apply_and_validate(",
    "                ticket_id,",
    "                typed_confirmation,",
    "                lambda path: _validate_edited_file(path, max_bytes),",
    "            )",
])
if bridge_normal.count(bridge_anchor) != 1:
    raise SystemExit(f"Expected exactly one generic approval apply block; found {bridge_normal.count(bridge_anchor)}.")

agent_dispatch = "\n".join([
    '            if ticket.get("ticket_kind") == "agent_project_edit":',
    "                from agent_safety_adapter_v2 import approve_agent_ticket, AgentSafetyError",
    "                try:",
    "                    result = approve_agent_ticket(",
    "                        ticket_id,",
    "                        typed_confirmation,",
    "                        expected_current,",
    "                        expected_proposed,",
    "                    )",
    "                except AgentSafetyError as exc:",
    '                    return _send(self, 409, {"ok": False, "error": str(exc)})',
    '                if result.get("status") == "validated":',
    "                    return _send(self, 200, result)",
    '                if result.get("status") == "rolled_back":',
    "                    return _send(self, 422, result)",
    "                return _send(self, 409, result)",
    bridge_anchor,
])
patched_bridge = bridge_normal.replace(bridge_anchor, agent_dispatch, 1)
ast.parse(patched_bridge, filename=str(bridge))

if agent_newline != "\n":
    patched_agent = patched_agent.replace("\n", agent_newline)
if bridge_newline != "\n":
    patched_bridge = patched_bridge.replace("\n", bridge_newline)
agent_bytes = (b"\xef\xbb\xbf" if agent_bom else b"") + patched_agent.encode("utf-8")
bridge_bytes = (b"\xef\xbb\xbf" if bridge_bom else b"") + patched_bridge.encode("utf-8")
ast.parse(patched_agent, filename=str(agent))
ast.parse(patched_bridge, filename=str(bridge))

stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime()) + f"_{int(time.time_ns() % 1000000):06d}"
agent_backup = backup_root / f"autonomous_agent.py.before_step8_{stamp}.bak"
bridge_backup = backup_root / f"workstation_safety_bridge.py.before_step8_{stamp}.bak"
for path in (agent_backup, bridge_backup):
    if path.exists():
        raise SystemExit(f"Backup collision: {path}")

backup_root.mkdir(parents=True, exist_ok=True)
shutil.copy2(agent, agent_backup)
shutil.copy2(bridge, bridge_backup)
if sha(agent_backup.read_bytes()) != expected_agent:
    raise SystemExit("Agent backup hash mismatch. No source patch made.")
if sha(bridge_backup.read_bytes()) != expected_bridge:
    raise SystemExit("Bridge backup hash mismatch. No source patch made.")
if sha(agent.read_bytes()) != expected_agent or sha(bridge.read_bytes()) != expected_bridge:
    raise SystemExit("A source changed during preparation. No source patch made.")

agent_tmp = agent.with_name(agent.name + ".step8.tmp")
bridge_tmp = bridge.with_name(bridge.name + ".step8.tmp")
if agent_tmp.exists() or bridge_tmp.exists():
    raise SystemExit("A Step 8 temporary source file already exists. No source patch made.")

for path, data in ((agent_tmp, agent_bytes), (bridge_tmp, bridge_bytes)):
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if sha(path.read_bytes()) != sha(data):
        raise SystemExit(f"Staged source hash mismatch: {path}")

if sha(agent.read_bytes()) != expected_agent or sha(bridge.read_bytes()) != expected_bridge:
    raise SystemExit("A source changed immediately before patch. No source patch made.")

# Apply Agent first; if bridge replacement fails, restore Agent from verified backup.
os.replace(agent_tmp, agent)
try:
    os.replace(bridge_tmp, bridge)
except Exception:
    if sha(agent.read_bytes()) == sha(agent_bytes) and sha(agent_backup.read_bytes()) == expected_agent:
        restore_tmp = agent.with_name(agent.name + ".step8.restore.tmp")
        shutil.copy2(agent_backup, restore_tmp)
        if sha(restore_tmp.read_bytes()) == expected_agent:
            os.replace(restore_tmp, agent)
    raise

if sha(agent.read_bytes()) != sha(agent_bytes) or sha(bridge.read_bytes()) != sha(bridge_bytes):
    raise SystemExit("Post-patch source hash mismatch. Preserve backups and inspect.")

manifest = {
    "phase": "3", "step": "8",
    "result": "PATCHED_PENDING_ADAPTER_RUNTIME_TEST",
    "timestamp_local": stamp,
    "autonomous_agent": str(agent),
    "agent_original_sha256": expected_agent,
    "agent_patched_sha256": sha(agent_bytes),
    "agent_backup": str(agent_backup),
    "agent_backup_sha256": sha(agent_backup.read_bytes()),
    "bridge": str(bridge),
    "bridge_original_sha256": expected_bridge,
    "bridge_patched_sha256": sha(bridge_bytes),
    "bridge_backup": str(bridge_backup),
    "bridge_backup_sha256": sha(bridge_backup.read_bytes()),
    "design": "Agent writes create multi-root approval tickets; run_task pauses; Safety Panel approval dispatches Agent-specific guarded apply and rollback.",
    "safe_file_ops_modified": False,
    "recovery_ops_modified": False,
    "config_modified": False
}
manifest_path = logs / f"PHASE3_STEP8_INSTALL_MANIFEST_{stamp}.json"
with manifest_path.open("x", encoding="utf-8") as stream:
    json.dump(manifest, stream, indent=2)
print(json.dumps({
    "manifest": str(manifest_path),
    "agent_backup": str(agent_backup),
    "bridge_backup": str(bridge_backup),
    "agent_patched_sha256": sha(agent_bytes),
    "bridge_patched_sha256": sha(bridge_bytes)
}, indent=2))