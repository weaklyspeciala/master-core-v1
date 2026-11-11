import ast
import hashlib
import json
import pathlib
import re
import sys
import time

root = pathlib.Path(sys.argv[1]).resolve()
core = root / "MASTER_CORE_V1"
agent_path = root / "autonomous_agent.py"
config_path = root / "config.json"
bridge_path = core / "integration" / "workstation_safety_bridge.py"
report_dir = core / "logs"

agent_raw = agent_path.read_bytes()
agent_text = agent_raw.decode("utf-8-sig")
agent_hash = hashlib.sha256(agent_raw).hexdigest()
tree = ast.parse(agent_text, filename=str(agent_path))
lines = agent_text.splitlines()
config = json.loads(config_path.read_text(encoding="utf-8-sig"))
bridge_raw = bridge_path.read_bytes()

report = []
def add(value=""):
    report.append(str(value))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

add("# Phase 3 Step 8 - Agent Integration Read-Only Audit")
add()
add(f"- Timestamp local: {time.strftime('%Y-%m-%d %H:%M:%S')}")
add(f"- Workspace root: {root}")
add("- Inspection mode: AST + source text only")
add("- Project code imported/executed: NO")
add("- Source/config modified: NO")
add()

add("## Source fingerprints")
add()
add(f"- autonomous_agent.py SHA256: `{agent_hash}`")
add(f"- autonomous_agent.py lines: {len(lines)}")
add(f"- config.json SHA256: `{sha(config_path)}`")
add(f"- workstation safety bridge SHA256: `{hashlib.sha256(bridge_raw).hexdigest()}`")
add()

add("## Model and project configuration (selected non-secret fields)")
add()
for key in (
    "ollama_url", "model", "fast_model", "deep_model",
    "default_mode", "fast_num_ctx", "deep_num_ctx",
    "num_ctx", "project_roots", "max_file_bytes",
    "command_timeout_seconds", "allow_python_compile",
    "allow_node_check", "allow_pytest", "allow_npm_test"
):
    if key in config:
        add(f"- `{key}`: `{json.dumps(config[key], ensure_ascii=False)}`")
add()

add("## Python top-level structure")
add()
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        add(f"- `{type(node).__name__} {node.name}`: lines {node.lineno}-{getattr(node, 'end_lineno', node.lineno)}")
    elif isinstance(node, (ast.Assign, ast.AnnAssign)):
        names = []
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                names.append(target.id)
        if names and any(token in ",".join(names).lower() for token in ("tool", "root", "cfg", "model", "backup", "audit", "system")):
            add(f"- top-level assignment `{', '.join(names)}`: line {node.lineno}")
add()

interesting = (
    "roots", "resolve_project", "trusted_project_roots", "allowed_root_for",
    "display_path", "safe_file", "tool_write", "tool_check", "ollama",
    "run_agent", "agent_loop", "execute", "main", "call_model",
    "dispatch", "process_tool", "ask"
)
selected = []
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if any(token in node.name.lower() for token in interesting):
            selected.append(node)

priority = {
    "tool_write": 0, "safe_file": 1, "allowed_root_for": 2,
    "resolve_project": 3, "roots": 4, "ollama": 5,
    "run_agent": 6, "main": 7
}
selected.sort(key=lambda node: (priority.get(node.name, 50), node.lineno))

secret_pattern = re.compile(r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|password|client[_-]?secret)(\s*[:=]\s*)([^\s,]+)")

add("## Relevant function source")
add()
add("The following functions are extracted from the current local source. Line numbers are preserved.")
add()
for node in selected:
    end_line = getattr(node, "end_lineno", node.lineno)
    add(f"### `{node.name}` (lines {node.lineno}-{end_line})")
    add()
    add("```python")
    for index in range(node.lineno - 1, end_line):
        source_line = secret_pattern.sub(r"\1\2[REDACTED]", lines[index])
        add(f"{index + 1:5}: {source_line}")
    add("```")
    add()

add("## Tool registry and routing references")
add()
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr in ("get", "append", "pop") and node.lineno:
            snippet = lines[node.lineno - 1].strip()
            if any(word in snippet.lower() for word in ("tool", "function", "messages", "choices", "call")):
                add(f"- line {node.lineno}: `{snippet[:240]}`")
add()

add("## Safety compatibility analysis")
add()
add("- Current Agent project roots can include multiple directories, including the separate Stickman repository.")
add("- The Step 6 safe_file_ops module is intentionally restricted to the MASTER workspace root.")
add("- Therefore Step 8 must use an agent-specific trusted-root resolver rather than passing external project paths into safe_file_ops.safe_target().")
add("- A compatible design must keep approval tickets in MASTER_CORE_V1 but store the approved target's trusted-root identity, relative path, original SHA256 and proposed SHA256.")
add("- Apply must re-resolve the selected project root, reject path escapes, backup original bytes, verify backup, recheck target hash, atomically replace, run configured static validation, and restore only if the target still matches the just-written SHA256.")
add("- Existing tool_check policy and disabled-by-default test commands must remain unchanged.")
add("- The local Approval Panel should list both workstation-file and Agent-project tickets, and approval must dispatch by ticket kind.")
add()

add("## Read-only audit result")
add()
add(f"- Functions selected for detailed review: {len(selected)}")
add("- Project code executed: NO")
add("- Source/config files modified: NO")
add("- Next step: build a separately backed-up Agent safety adapter and extend the approval bridge/panel with an agent-project ticket handler.")
add()

stamp = time.strftime("%Y%m%d_%H%M%S")
report_path = report_dir / f"PHASE3_STEP8_AGENT_INTEGRATION_AUDIT_{stamp}.md"
with report_path.open("x", encoding="utf-8") as f:
    f.write("\n".join(report))
print(f"PHASE3_STEP8_AUDIT_COMPLETE={report_path}")
print(f"AUTONOMOUS_AGENT_SHA256={agent_hash}")
print(f"FUNCTIONS_EXTRACTED={len(selected)}")
print("PROJECT_CODE_EXECUTED=NO")
print("SOURCE_FILES_MODIFIED=NO")