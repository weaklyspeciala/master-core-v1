import ast, hashlib, json, os, pathlib, shutil, sys, time

workstation = pathlib.Path(sys.argv[1]).resolve()
bridge = pathlib.Path(sys.argv[2]).resolve()
core = pathlib.Path(sys.argv[3]).resolve()
expected = sys.argv[4].lower()
backup_dir = core / "backups"
logs_dir = core / "logs"

def sha(data):
    return hashlib.sha256(data).hexdigest()

raw = workstation.read_bytes()
actual = sha(raw)
if actual != expected:
    raise SystemExit(f"workstation.py hash mismatch: expected {expected}, found {actual}")

bridge_bytes = bridge.read_bytes()
ast.parse(bridge_bytes.decode("utf-8"), filename=str(bridge))

has_bom = raw.startswith(b"\xef\xbb\xbf")
text = raw.decode("utf-8-sig")
newline = "\r\n" if b"\r\n" in raw else "\n"
normal = text.replace("\r\n", "\n").replace("\r", "\n")
tree = ast.parse(normal, filename=str(workstation))

guards = []
for node in tree.body:
    if isinstance(node, ast.If):
        test = node.test
        if isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) and test.left.id == "__name__":
            if any(isinstance(op, ast.Eq) for op in test.ops):
                if any(isinstance(value, ast.Constant) and value.value == "__main__" for value in test.comparators):
                    guards.append(node)

if len(guards) != 1:
    raise SystemExit(f"Expected exactly one top-level __main__ guard; found {len(guards)}. No workstation patch made.")

guard_line = guards[0].lineno - 1
lines = normal.splitlines()
marker = "# MASTER_CORE_V1 PHASE 3 STEP 6 SAFE BRIDGE"
if marker in normal:
    raise SystemExit("Step 6 bridge marker already exists. No patch made.")

bootstrap = [
    marker,
    "import sys as _p3_sys",
    "from pathlib import Path as _p3_Path",
    "_p3_integration_dir = _p3_Path(__file__).resolve().parent / 'MASTER_CORE_V1' / 'integration'",
    "if str(_p3_integration_dir) not in _p3_sys.path:",
    "    _p3_sys.path.insert(0, str(_p3_integration_dir))",
    "import workstation_safety_bridge as _p3_safe_bridge",
    "_p3_safe_bridge.install(globals())",
    "",
]
new_lines = lines[:guard_line] + bootstrap + lines[guard_line:]
patched_text = "\n".join(new_lines) + ("\n" if normal.endswith("\n") else "")
if newline != "\n":
    patched_text = patched_text.replace("\n", newline)
patched_bytes = (b"\xef\xbb\xbf" if has_bom else b"") + patched_text.encode("utf-8")
ast.parse(patched_text, filename=str(workstation))

stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime()) + f"_{int(time.time_ns() % 1000000):06d}"
backup = backup_dir / f"workstation.py.before_step6_{stamp}.bak"
if backup.exists():
    raise SystemExit(f"Backup collision: {backup}")

backup_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(workstation, backup)
if sha(backup.read_bytes()) != actual:
    raise SystemExit("Source backup verification failed. Original workstation.py was not changed.")

if sha(workstation.read_bytes()) != expected:
    raise SystemExit("workstation.py changed during patch preparation. Original was not changed.")

tmp = workstation.with_name(workstation.name + ".step6.tmp")
if tmp.exists():
    raise SystemExit(f"Temporary patch file already exists: {tmp}")
with tmp.open("xb") as f:
    f.write(patched_bytes)
    f.flush()
    os.fsync(f.fileno())

if sha(tmp.read_bytes()) != sha(patched_bytes):
    raise SystemExit("Staged workstation patch hash mismatch. Original was not changed.")
if sha(workstation.read_bytes()) != expected:
    tmp.unlink()
    raise SystemExit("workstation.py changed immediately before patch. Original was not changed.")

os.replace(tmp, workstation)
patched_hash = sha(workstation.read_bytes())

manifest = {
    "phase": "3",
    "step": "6",
    "result": "PATCHED_PENDING_RUNTIME_TEST",
    "timestamp_local": stamp,
    "workstation": str(workstation),
    "original_sha256": actual,
    "patched_sha256": patched_hash,
    "backup": str(backup),
    "backup_sha256": sha(backup.read_bytes()),
    "bridge_module": str(bridge),
    "bridge_sha256": sha(bridge_bytes),
    "method": "AST-located bootstrap insertion before top-level __main__ guard; atomic replacement",
    "legacy_autonomous_agent_modified": False
}
manifest_path = logs_dir / f"PHASE3_STEP6_INSTALL_MANIFEST_{stamp}.json"
with manifest_path.open("x", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
print(json.dumps({"manifest": str(manifest_path), "backup": str(backup),
                  "original_sha256": actual, "patched_sha256": patched_hash,
                  "bridge_sha256": sha(bridge_bytes)}, indent=2))