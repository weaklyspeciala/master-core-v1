"""Safe file-operation primitives for MASTER_CORE_V1.

Not connected to legacy agents or a web server.
Callers must obtain explicit human approval for every edit.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

CORE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = CORE_ROOT.parent.resolve()
BACKUP_ROOT = (CORE_ROOT / "backups").resolve()
APPROVAL_ROOT = (CORE_ROOT / "approvals").resolve()
LOG_PATH = CORE_ROOT / "logs" / "safety_audit.jsonl"
TICKET_TTL_SECONDS = 600


class SafetyError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def safe_target(relative_path: str) -> Path:
    """Resolve a workspace-relative target and reject path traversal."""
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise SafetyError("A non-empty relative path is required.")
    candidate = (WORKSPACE_ROOT / relative_path).resolve()
    if candidate == WORKSPACE_ROOT or not _inside(candidate, WORKSPACE_ROOT):
        raise SafetyError("Target must remain inside the workspace.")
    if _inside(candidate, CORE_ROOT):
        raise SafetyError("Phase 3 core files are protected from this generic writer.")
    if candidate.exists() and candidate.is_dir():
        raise SafetyError("Target is a directory, not a file.")
    return candidate


def _audit(event: str, details: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
        "details": details,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def create_approval_ticket(relative_path: str, proposed_content: str) -> dict:
    """Create a short-lived ticket; this does NOT approve or apply the edit."""
    target = safe_target(relative_path)
    if not target.parent.exists():
        raise SafetyError("Target parent directory must already exist.")
    if not target.exists():
        raise SafetyError("This initial version only supports edits to existing files.")
    if not isinstance(proposed_content, str):
        raise SafetyError("Proposed content must be text.")

    current_hash = sha256_file(target)
    proposed_hash = sha256_bytes(proposed_content.encode("utf-8"))
    ticket = {
        "ticket_id": str(uuid.uuid4()),
        "created_at": time.time(),
        "expires_at": time.time() + TICKET_TTL_SECONDS,
        "relative_path": target.relative_to(WORKSPACE_ROOT).as_posix(),
        "current_sha256": current_hash,
        "proposed_sha256": proposed_hash,
        "proposed_content": proposed_content,
        "status": "pending",
    }
    ticket_path = APPROVAL_ROOT / (ticket["ticket_id"] + ".json")
    ticket_path.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
    _audit("approval_ticket_created", {
        "ticket_id": ticket["ticket_id"],
        "path": ticket["relative_path"],
        "current_sha256": current_hash,
        "proposed_sha256": proposed_hash,
        "expires_at": ticket["expires_at"],
    })
    # Do not return proposed content to callers as part of the ticket summary.
    return {k: v for k, v in ticket.items() if k != "proposed_content"}


def reject_approval(ticket_id: str) -> dict:
    ticket_path = APPROVAL_ROOT / (ticket_id + ".json")
    if not _inside(ticket_path, APPROVAL_ROOT) or not ticket_path.is_file():
        raise SafetyError("Approval ticket not found.")
    ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
    if ticket.get("status") != "pending":
        raise SafetyError("Ticket is no longer pending.")
    ticket["status"] = "rejected"
    ticket["proposed_content"] = ""
    ticket_path.write_text(json.dumps(ticket, indent=2), encoding="utf-8")
    _audit("approval_rejected", {"ticket_id": ticket_id, "path": ticket["relative_path"]})
    return {"ok": True, "status": "rejected", "ticket_id": ticket_id}


def approve_and_apply(ticket_id: str, typed_confirmation: str) -> dict:
    """Apply only after caller supplies exact confirmation text APPROVE."""
    if typed_confirmation != "APPROVE":
        raise SafetyError("Explicit confirmation text must be exactly APPROVE.")

    ticket_path = APPROVAL_ROOT / (ticket_id + ".json")
    if not _inside(ticket_path, APPROVAL_ROOT) or not ticket_path.is_file():
        raise SafetyError("Approval ticket not found.")
    ticket = json.loads(ticket_path.read_text(encoding="utf-8"))

    if ticket.get("status") != "pending":
        raise SafetyError("Ticket is no longer pending.")
    if time.time() > float(ticket.get("expires_at", 0)):
        ticket["status"] = "expired"
        ticket["proposed_content"] = ""
        ticket_path.write_text(json.dumps(ticket, indent=2), encoding="utf-8")
        _audit("approval_expired", {"ticket_id": ticket_id})
        raise SafetyError("Approval ticket expired. Create a new ticket.")

    target = safe_target(ticket["relative_path"])
    if not target.is_file():
        raise SafetyError("Target file no longer exists.")
    current_hash = sha256_file(target)
    if current_hash != ticket["current_sha256"]:
        raise SafetyError("Target changed after review. Approval invalidated.")
    content = ticket.get("proposed_content", "")
    proposed_hash = sha256_bytes(content.encode("utf-8"))
    if proposed_hash != ticket["proposed_sha256"]:
        raise SafetyError("Proposed content integrity check failed.")

    # Backup first, and verify it before changing the original.
    stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    backup_name = f"{target.name}.{stamp}.{ticket_id[:8]}.bak"
    backup_path = BACKUP_ROOT / backup_name
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    original_bytes = target.read_bytes()
    backup_path.write_bytes(original_bytes)
    if sha256_file(backup_path) != current_hash:
        raise SafetyError("Backup verification failed; original was not changed.")

    # Recheck target immediately before atomic replacement.
    if sha256_file(target) != current_hash:
        raise SafetyError("Target changed during approval; original was not changed.")

    temp_name: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", delete=False,
            dir=str(target.parent), prefix=".mastercore_", suffix=".tmp"
        ) as tmp:
            temp_name = tmp.name
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())

        if sha256_file(Path(temp_name)) != proposed_hash:
            raise SafetyError("Staged content verification failed.")

        os.replace(temp_name, target)
        temp_name = None
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)

    final_hash = sha256_file(target)
    if final_hash != proposed_hash:
        # Preserve the verified backup; do not attempt an unverified automatic rollback.
        _audit("post_write_hash_mismatch", {
            "ticket_id": ticket_id, "path": ticket["relative_path"],
            "backup": str(backup_path), "expected": proposed_hash, "actual": final_hash
        })
        raise SafetyError("Post-write verification failed. Verified backup retained for manual recovery.")

    ticket["status"] = "applied"
    ticket["proposed_content"] = ""
    ticket["applied_at"] = time.time()
    ticket["backup_path"] = str(backup_path)
    ticket["final_sha256"] = final_hash
    ticket_path.write_text(json.dumps(ticket, indent=2), encoding="utf-8")
    _audit("approved_edit_applied", {
        "ticket_id": ticket_id, "path": ticket["relative_path"],
        "backup": str(backup_path), "sha256": final_hash
    })
    return {
        "ok": True,
        "status": "applied",
        "path": ticket["relative_path"],
        "backup": str(backup_path),
        "sha256": final_hash,
    }