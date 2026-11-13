"""Narrow policy for generated-code auto approval."""
from pathlib import PurePosixPath
POLICY_VERSION = "1.0"
AUTO_PREFIXES = ("staging/generated/", "workspace/generated/", "modules/generated/")
AUTO_EXTENSIONS = {".py", ".json", ".md", ".txt", ".js", ".mjs", ".html", ".css", ".yml", ".yaml", ".toml"}
DENY_NAMES = {"safety_policy.md", "agent_safety_adapter.py", "agent_safety_adapter_v2.py", "agent_autonomy_policy.py", "master_self_upgrade_runtime.py", "self_development_controller_v1.py", "autonomous_quality_gate.py", "master_studio_agent.py", "config.json", ".env", "secrets.json", "credentials.json", "token.json"}
DENY_PARTS = {".git", "approvals", "backups", "logs", "secrets", "credentials"}
def evaluate(relative_path, content):
    rel = str(relative_path).replace("\\", "/").lstrip("./")
    parts = [p.lower() for p in rel.split("/") if p]
    if not rel or ".." in parts: return False, "invalid path"
    if any(p in DENY_PARTS for p in parts) or parts[-1] in DENY_NAMES: return False, "protected path"
    if PurePosixPath(rel).suffix.lower() not in AUTO_EXTENSIONS: return False, "extension not eligible"
    if not any(rel.startswith(p) for p in AUTO_PREFIXES): return False, "outside generated-code zones"
    if not isinstance(content, str) or not content.strip() or len(content.encode("utf-8")) > 250000: return False, "empty or too large"
    return True, "policy-v1 generated-code allowlist"
