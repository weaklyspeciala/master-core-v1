import ast, hashlib, json, os, pathlib, shutil, sys, time
bridge = pathlib.Path(sys.argv[1]).resolve()
panel = pathlib.Path(sys.argv[2]).resolve()
core = pathlib.Path(sys.argv[3]).resolve()
expected = sys.argv[4].lower()
backup_dir = core / "backups"
logs_dir = core / "logs"

def sha(data):
    return hashlib.sha256(data).hexdigest()

raw = bridge.read_bytes()
actual = sha(raw)
if actual != expected:
    raise SystemExit(f"Bridge hash mismatch: expected {expected}, found {actual}")
text = raw.decode("utf-8-sig")
anchor = "\n".join([
    "    def wrapped_get(self):",
    "        parsed = urlparse(self.path)",
    "        if parsed.path not in {\"/api/safety/pending\", \"/api/safety/ticket\"}:",
])
if text.count(anchor) != 1:
    raise SystemExit(f"Expected exactly one wrapped_get anchor; found {text.count(anchor)}")
replacement = "\n".join([
    "    def wrapped_get(self):",
    "        parsed = urlparse(self.path)",
    "        if parsed.path == \"/safety\":",
    "            from approval_panel import render_panel",
    "            return self.send_data(200, render_panel(), \"text/html; charset=utf-8\")",
    "        if parsed.path not in {\"/api/safety/pending\", \"/api/safety/ticket\"}:",
])
patched = text.replace(anchor, replacement, 1)
ast.parse(patched, filename=str(bridge))
ast.parse(panel.read_text(encoding="utf-8"), filename=str(panel))

stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime()) + f"_{int(time.time_ns() % 1000000):06d}"
backup = backup_dir / f"workstation_safety_bridge.py.before_step7_{stamp}.bak"
if backup.exists():
    raise SystemExit(f"Backup collision: {backup}")
shutil.copy2(bridge, backup)
if sha(backup.read_bytes()) != actual:
    raise SystemExit("Bridge backup verification failed. Original bridge was not changed.")
if sha(bridge.read_bytes()) != expected:
    raise SystemExit("Bridge changed during patch preparation.")
patched_bytes = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + patched.encode("utf-8")
tmp = bridge.with_name(bridge.name + ".step7.tmp")
if tmp.exists():
    raise SystemExit(f"Temporary file exists: {tmp}")
with tmp.open("xb") as f:
    f.write(patched_bytes)
    f.flush()
    os.fsync(f.fileno())
if sha(tmp.read_bytes()) != sha(patched_bytes):
    raise SystemExit("Staged bridge patch hash mismatch.")
if sha(bridge.read_bytes()) != expected:
    tmp.unlink()
    raise SystemExit("Bridge changed immediately before atomic patch.")
os.replace(tmp, bridge)
patched_hash = sha(bridge.read_bytes())
manifest = {
    "phase": "3", "step": "7", "result": "PANEL_INSTALLED_PENDING_RESTART",
    "timestamp_local": stamp, "bridge": str(bridge),
    "original_sha256": actual, "patched_sha256": patched_hash,
    "backup": str(backup), "backup_sha256": sha(backup.read_bytes()),
    "panel_module": str(panel), "panel_sha256": sha(panel.read_bytes()),
    "route": "/safety", "workstation_py_modified": False
}
manifest_path = logs_dir / f"PHASE3_STEP7_INSTALL_MANIFEST_{stamp}.json"
with manifest_path.open("x", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
print(json.dumps({"manifest": str(manifest_path), "bridge_backup": str(backup),
                  "bridge_original_sha256": actual, "bridge_patched_sha256": patched_hash,
                  "panel_sha256": sha(panel.read_bytes())}, indent=2))