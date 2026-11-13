"""Multi-project approval adapter for MASTER AI WORKSTATION Agent.

Approval tickets are stored in MASTER_CORE_V1/approvals so the local Safety
Approval Panel can display and approve them. Targets are resolved against the
current config.json trusted project roots at both ticket creation and approval.
No target file is changed until the human approval endpoint applies the ticket.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

CORE_ROOT = Path(__file__).resolve().parents[1]
MASTER_ROOT = CORE_ROOT.parent.resolve()
APPROVAL_ROOT = (CORE_ROOT / "approvals").resolve()
BACKUP_ROOT = (CORE_ROOT / "backups" / "agent_project_edits").resolve()
LOG_PATH = CORE_ROOT / "logs" / "agent_safety_audit.jsonl"
TICKET_TTL_SECONDS = 600
MAX_TEXT_BYTES = 1_000_000
ALLOWED_EXTENSIONS = {".py", ".js", ".mjs", ".cjs", ".json", ".html", ".css", ".md", ".txt", ".yml", ".yaml", ".toml", ".ps1"}
_LOCK = threading.RLock()


class AgentSafetyError(ValueError):
    pass


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def _audit(event: str, details: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
        "details": details,
    }
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def _configured_roots() -> list[Path]:
    config_path = MASTER_ROOT / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise AgentSafetyError(f"Cannot load trusted project configuration: {exc}") from exc

    candidates: list[Path] = []
    for raw in config.get("project_roots", []):
        candidate = Path(os.path.expandvars(str(raw))).expanduser()
        if candidate.exists() and candidate.is_dir():
            resolved = candidate.resolve()
            if resolved not in candidates:
                candidates.append(resolved)

    # Match autonomous_agent.roots(): the local Agent workspace is trusted too.
    agent_workspace = (MASTER_ROOT / "workspace").resolve()
    if agent_workspace.exists() and agent_workspace.is_dir() and agent_workspace not in candidates:
        candidates.append(agent_workspace)

    if not candidates:
        raise AgentSafetyError("No configured trusted project roots are currently available.")
    return candidates


def _validate_selected_project(selected_project: Path, configured_roots: list[Path]) -> Path:
    selected = selected_project.resolve()
    if not selected.exists() or not selected.is_dir():
        raise AgentSafetyError("Selected Agent project no longer exists.")
    if not any(_inside(selected, root) for root in configured_roots):
        raise AgentSafetyError("Selected project is no longer inside a configured trusted root.")
    return selected


def _trusted_root_for(target: Path, selected_project: Path, configured_roots: list[Path]) -> Path:
    selected = _validate_selected_project(selected_project, configured_roots)
    candidates = [selected] + list(configured_roots)
    unique: list[Path] = []
    for item in candidates:
        resolved = item.resolve()
        if resolved.exists() and resolved.is_dir() and resolved not in unique:
            unique.append(resolved)
    unique.sort(key=lambda item: len(item.parts), reverse=True)

    resolved_target = target.resolve()
    for candidate in unique:
        if _inside(resolved_target, candidate):
            return candidate
    raise AgentSafetyError("Target is outside all currently configured trusted project roots.")


def _ticket_path(ticket_id: str) -> Path:
    try:
        canonical = str(uuid.UUID(str(ticket_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise AgentSafetyError("Invalid approval ticket ID.") from exc
    path = (APPROVAL_ROOT / (canonical + ".json")).resolve()
    if not _inside(path, APPROVAL_ROOT):
        raise AgentSafetyError("Ticket path is outside the approval store.")
    return path


def _read_ticket(ticket_id: str) -> tuple[Path, dict]:
    path = _ticket_path(ticket_id)
    if not path.is_file():
        raise AgentSafetyError("Agent approval ticket not found.")
    try:
        ticket = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AgentSafetyError(f"Agent approval ticket is unreadable: {exc}") from exc
    if ticket.get("ticket_id") != str(uuid.UUID(ticket_id)):
        raise AgentSafetyError("Ticket ID does not match ticket content.")
    if ticket.get("ticket_kind") != "agent_project_edit":
        raise AgentSafetyError("This is not an Agent project-edit ticket.")
    return path, ticket


def _write_ticket(path: Path, ticket: dict) -> None:
    temp = path.with_name(path.name + ".tmp")
    if temp.exists():
        raise AgentSafetyError("Ticket update temp file already exists; refusing overwrite.")
    payload = json.dumps(ticket, ensure_ascii=False, indent=2).encode("utf-8")
    with temp.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)



def _ensure_approved_parent(target: Path, trusted_root: Path) -> None:
    """Create missing parent folders only after ticket approval."""
    root = Path(trusted_root).resolve()
    parent = Path(target).parent

    if not _inside(parent.resolve(), root):
        raise AgentSafetyError("Target parent is outside the trusted project root.")

    missing = []
    cursor = parent

    while not cursor.exists():
        missing.append(cursor)
        next_cursor = cursor.parent
        if next_cursor == cursor:
            raise AgentSafetyError("Cannot locate an existing trusted parent.")
        cursor = next_cursor

    existing = cursor.resolve()
    if not _inside(existing, root) or not existing.is_dir():
        raise AgentSafetyError("Nearest existing parent is not inside the trusted root.")

    created = []
    try:
        for directory in reversed(missing):
            parent_resolved = directory.parent.resolve()
            if not _inside(parent_resolved, root):
                raise AgentSafetyError("Directory creation escaped the trusted root.")

            try:
                directory.mkdir()
                created.append(directory)
            except FileExistsError:
                pass

            if directory.is_symlink():
                raise AgentSafetyError("Symlink directory creation is not permitted.")

            resolved = directory.resolve()
            if not _inside(resolved, root) or not directory.is_dir():
                raise AgentSafetyError("Created directory failed trusted-root validation.")
    except Exception:
        for directory in reversed(created):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise


def create_agent_ticket(
    target: Path,
    selected_project: Path,
    display_path: str,
    proposed_content: str,
    max_bytes: int = MAX_TEXT_BYTES,
) -> dict:
    if not isinstance(proposed_content, str):
        raise AgentSafetyError("Proposed content must be text.")
    content_bytes = proposed_content.encode("utf-8")
    if len(content_bytes) > min(int(max_bytes), MAX_TEXT_BYTES):
        raise AgentSafetyError("Proposed file exceeds the configured Agent file-size limit.")

    resolved_target = Path(target).resolve()
    selected = Path(selected_project).resolve()
    configured = _configured_roots()
    trusted_root = _trusted_root_for(resolved_target, selected, configured)

    if resolved_target.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise AgentSafetyError("File extension is not enabled for Agent editing.")
    if resolved_target.exists() and not resolved_target.is_file():
        raise AgentSafetyError("Target is not a regular file.")

    if resolved_target.exists():
        try:
            original_bytes = resolved_target.read_bytes()
            original_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AgentSafetyError("Existing target is not UTF-8 text.") from exc
        current_hash = _sha_bytes(original_bytes)
        target_existed = True
    else:
        current_hash = None
        target_existed = False

    ticket_id = str(uuid.uuid4())
    now = time.time()
    relative_to_root = resolved_target.relative_to(trusted_root).as_posix()
    ticket = {
        "ticket_id": ticket_id,
        "ticket_kind": "agent_project_edit",
        "status": "pending",
        "relative_path": str(display_path),
        "target_root": str(trusted_root),
        "target_relative_path": relative_to_root,
        "selected_project": str(selected),
        "target_existed": target_existed,
        "current_sha256": current_hash,
        "proposed_sha256": _sha_bytes(content_bytes),
        "proposed_content": proposed_content,
        "created_at": now,
        "expires_at": now + TICKET_TTL_SECONDS,
    }

    APPROVAL_ROOT.mkdir(parents=True, exist_ok=True)
    ticket_path = _ticket_path(ticket_id)
    with _LOCK:
        with ticket_path.open("x", encoding="utf-8") as stream:
            json.dump(ticket, stream, ensure_ascii=False, indent=2)
    _audit("agent_approval_ticket_created", {
        "ticket_id": ticket_id,
        "path": ticket["relative_path"],
        "target_root": str(trusted_root),
        "target_relative_path": relative_to_root,
        "target_existed": target_existed,
        "current_sha256": current_hash,
        "proposed_sha256": ticket["proposed_sha256"],
        "expires_at": ticket["expires_at"],
    })
    return {
        key: value for key, value in ticket.items()
        if key not in {"proposed_content", "target_root", "target_relative_path", "selected_project"}
    }


def _resolve_ticket_target(ticket: dict) -> tuple[Path, Path]:
    configured = _configured_roots()
    selected = _validate_selected_project(Path(ticket["selected_project"]), configured)
    trusted_root = Path(ticket["target_root"]).resolve()

    # The recorded root must still be either the selected project or a configured root.
    if trusted_root != selected and trusted_root not in configured:
        raise AgentSafetyError("Recorded trusted root is no longer configured.")
    if not trusted_root.exists() or not trusted_root.is_dir():
        raise AgentSafetyError("Recorded trusted root no longer exists.")

    relative = ticket.get("target_relative_path")
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ":" in relative:
        raise AgentSafetyError("Ticket target path is invalid.")
    target = (trusted_root / relative).resolve()
    if not _inside(target, trusted_root):
        raise AgentSafetyError("Ticket target escaped its recorded trusted root.")
    # Re-run the current trust-root chooser, so config/root changes invalidate tickets.
    current_root = _trusted_root_for(target, selected, configured)
    if current_root != trusted_root:
        raise AgentSafetyError("The target's most-specific trusted root changed after ticket creation.")
    if target.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise AgentSafetyError("Ticket target extension is no longer allowed.")
    return target, trusted_root


def _validate_bytes(target: Path, content: bytes) -> tuple[bool, str | None]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return False, "Proposed content is not valid UTF-8."
    suffix = target.suffix.lower()
    try:
        if suffix == ".py":
            compile(text, str(target), "exec")
        elif suffix == ".json":
            json.loads(text)
    except (SyntaxError, json.JSONDecodeError, ValueError) as exc:
        return False, f"Static validation failed: {exc}"
    return True, None


def _atomic_restore(target: Path, backup: Path, expected_current: str, expected_backup: str) -> str:
    if not target.is_file():
        raise AgentSafetyError("Rollback target disappeared; manual recovery required.")
    if _sha_file(target) != expected_current:
        raise AgentSafetyError("Target changed after apply; rollback refused to overwrite newer content.")
    if not backup.is_file() or _sha_file(backup) != expected_backup:
        raise AgentSafetyError("Verified backup is unavailable or changed; manual recovery required.")

    staged_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=str(target.parent),
                                         prefix=".master_agent_restore_", suffix=".tmp") as stream:
            staged_name = stream.name
            with backup.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())

        staged = Path(staged_name)
        if _sha_file(staged) != expected_backup:
            raise AgentSafetyError("Staged rollback content failed SHA256 verification.")
        if _sha_file(target) != expected_current:
            raise AgentSafetyError("Target changed immediately before rollback; restore refused.")
        if _sha_file(backup) != expected_backup:
            raise AgentSafetyError("Backup changed immediately before rollback.")
        os.replace(str(staged), str(target))
        staged_name = None
        restored_hash = _sha_file(target)
        if restored_hash != expected_backup:
            raise AgentSafetyError("Post-rollback hash mismatch; inspect backup and target manually.")
        return restored_hash
    finally:
        if staged_name and os.path.exists(staged_name):
            try:
                os.unlink(staged_name)
            except OSError:
                pass


def reject_agent_ticket(ticket_id: str, reason: str) -> dict:
    """Reject a pending Agent project-edit ticket without changing its target."""
    if not isinstance(reason, str):
        raise AgentSafetyError("Rejection reason must be text.")

    clean_reason = reason.strip()
    if not clean_reason:
        raise AgentSafetyError("A non-empty rejection reason is required.")
    if len(clean_reason) > 2000:
        raise AgentSafetyError("Rejection reason must be 2000 characters or fewer.")

    with _LOCK:
        ticket_path, ticket = _read_ticket(ticket_id)

        if ticket.get("status") != "pending":
            raise AgentSafetyError("Agent ticket is no longer pending.")

        was_expired = time.time() > float(ticket.get("expires_at", 0))

        ticket["status"] = "rejected"
        ticket["rejected_at"] = time.time()
        ticket["rejection_reason"] = clean_reason
        ticket["was_expired_when_rejected"] = was_expired
        ticket["proposed_content"] = ""

        _write_ticket(ticket_path, ticket)
        _audit("agent_approval_rejected", {
            "ticket_id": ticket_id,
            "path": ticket.get("relative_path"),
            "reason": clean_reason,
            "was_expired_when_rejected": was_expired,
        })

    return {
        "ok": True,
        "status": "rejected",
        "ticket_id": ticket_id,
        "was_expired_when_rejected": was_expired,
    }


def approve_agent_ticket(
    ticket_id: str,
    typed_confirmation: str,
    expected_current_sha256: str | None,
    expected_proposed_sha256: str,
) -> dict:
    if typed_confirmation != "APPROVE":
        raise AgentSafetyError("Explicit confirmation text must be exactly APPROVE.")

    with _LOCK:
        ticket_path, ticket = _read_ticket(ticket_id)
        if ticket.get("status") != "pending":
            raise AgentSafetyError("Agent ticket is no longer pending.")
        if time.time() > float(ticket.get("expires_at", 0)):
            ticket["status"] = "expired"
            ticket["proposed_content"] = ""
            _write_ticket(ticket_path, ticket)
            _audit("agent_approval_expired", {"ticket_id": ticket_id})
            raise AgentSafetyError("Agent approval ticket expired. Create a new edit proposal.")

        if expected_current_sha256 != ticket.get("current_sha256"):
            raise AgentSafetyError("Original-file SHA256 does not match the reviewed ticket.")
        if expected_proposed_sha256 != ticket.get("proposed_sha256"):
            raise AgentSafetyError("Proposed-content SHA256 does not match the reviewed ticket.")

        target, trusted_root = _resolve_ticket_target(ticket)
        proposed_bytes = ticket.get("proposed_content", "").encode("utf-8")
        proposed_hash = _sha_bytes(proposed_bytes)
        if proposed_hash != ticket.get("proposed_sha256"):
            raise AgentSafetyError("Stored proposed content no longer matches its SHA256.")

        existed = bool(ticket.get("target_existed"))
        if existed:
            if not target.is_file():
                raise AgentSafetyError("Original target disappeared; approval invalidated.")
            current_hash = _sha_file(target)
            if current_hash != ticket.get("current_sha256"):
                raise AgentSafetyError("Target changed after review; approval invalidated.")
            original_bytes = target.read_bytes()
            BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
            backup = BACKUP_ROOT / f"{ticket_id}.{target.name}.before.bak"
            with backup.open("xb") as stream:
                stream.write(original_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            if _sha_file(backup) != current_hash:
                raise AgentSafetyError("Agent backup verification failed; original was not changed.")
        else:
            backup = None
            if target.exists():
                raise AgentSafetyError("A file appeared at the new-file target after review; approval invalidated.")
            _ensure_approved_parent(target, trusted_root)

        # Re-resolve and recheck immediately before replacement/creation.
        target_check, root_check = _resolve_ticket_target(ticket)
        if target_check != target or root_check != trusted_root:
            raise AgentSafetyError("Target trust resolution changed during approval.")
        if existed:
            if _sha_file(target) != ticket.get("current_sha256"):
                raise AgentSafetyError("Target changed immediately before replacement.")
        elif target.exists():
            raise AgentSafetyError("Target appeared immediately before creation.")

        staged_name = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=str(target.parent),
                                             prefix=".master_agent_write_", suffix=".tmp") as stream:
                staged_name = stream.name
                stream.write(proposed_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            staged = Path(staged_name)
            if _sha_file(staged) != proposed_hash:
                raise AgentSafetyError("Staged Agent content failed SHA256 verification.")

            if existed:
                if _sha_file(target) != ticket.get("current_sha256"):
                    raise AgentSafetyError("Target changed immediately before atomic replacement.")
                os.replace(str(staged), str(target))
                staged_name = None
            else:
                # Exclusive creation prevents overwriting a file that appeared after review.
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                descriptor = os.open(str(target), flags, 0o666)
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(proposed_bytes)
                        stream.flush()
                        os.fsync(stream.fileno())
                except Exception:
                    try:
                        if target.is_file() and _sha_file(target) == proposed_hash:
                            target.unlink()
                    except OSError:
                        pass
                    raise
                staged.unlink()
                staged_name = None
        finally:
            if staged_name and os.path.exists(staged_name):
                try:
                    os.unlink(staged_name)
                except OSError:
                    pass

        if not target.is_file() or _sha_file(target) != proposed_hash:
            ticket["status"] = "recovery_required"
            ticket["backup"] = str(backup) if backup else None
            _write_ticket(ticket_path, ticket)
            _audit("agent_apply_hash_mismatch", {"ticket_id": ticket_id, "path": ticket["relative_path"]})
            return {
                "ok": False, "status": "recovery_required", "ticket_id": ticket_id,
                "path": ticket["relative_path"], "backup": str(backup) if backup else None,
                "recovery_error": "Applied file SHA256 did not match the approved proposal.",
            }

        # Static validation after the approved change. No project code is executed.
        validation_ok, validation_error = _validate_bytes(target, proposed_bytes)
        if not validation_ok:
            try:
                if existed:
                    restored_hash = _atomic_restore(target, backup, proposed_hash, ticket["current_sha256"])
                else:
                    if not target.is_file() or _sha_file(target) != proposed_hash:
                        raise AgentSafetyError("New target changed after creation; cleanup refused.")
                    target.unlink()
                    restored_hash = None
                ticket["status"] = "rolled_back"
                ticket["backup"] = str(backup) if backup else None
                ticket["validation_error"] = validation_error
                ticket["proposed_content"] = ""
                _write_ticket(ticket_path, ticket)
                _audit("agent_automatic_rollback_completed", {
                    "ticket_id": ticket_id, "path": ticket["relative_path"],
                    "backup": str(backup) if backup else None,
                    "restored_sha256": restored_hash,
                    "validation_error": validation_error,
                })
                return {
                    "ok": False, "status": "rolled_back", "ticket_id": ticket_id,
                    "path": ticket["relative_path"], "backup": str(backup) if backup else None,
                    "validation_passed": False, "validation_error": validation_error,
                    "restored_sha256": restored_hash,
                }
            except Exception as exc:
                ticket["status"] = "recovery_required"
                ticket["backup"] = str(backup) if backup else None
                ticket["validation_error"] = validation_error
                ticket["recovery_error"] = f"{type(exc).__name__}: {exc}"
                ticket["proposed_content"] = ""
                _write_ticket(ticket_path, ticket)
                _audit("agent_automatic_rollback_refused", {
                    "ticket_id": ticket_id, "path": ticket["relative_path"],
                    "backup": str(backup) if backup else None,
                    "validation_error": validation_error,
                    "recovery_error": ticket["recovery_error"],
                })
                return {
                    "ok": False, "status": "recovery_required", "ticket_id": ticket_id,
                    "path": ticket["relative_path"], "backup": str(backup) if backup else None,
                    "validation_passed": False, "validation_error": validation_error,
                    "recovery_error": ticket["recovery_error"],
                }

        ticket["status"] = "applied"
        ticket["backup"] = str(backup) if backup else None
        ticket["applied_sha256"] = proposed_hash
        ticket["proposed_content"] = ""
        _write_ticket(ticket_path, ticket)
        _audit("agent_project_edit_applied", {
            "ticket_id": ticket_id, "path": ticket["relative_path"],
            "target_root": str(trusted_root),
            "backup": str(backup) if backup else None,
            "applied_sha256": proposed_hash,
        })
        return {
            "ok": True, "status": "validated", "ticket_id": ticket_id,
            "path": ticket["relative_path"], "sha256": proposed_hash,
            "backup": str(backup) if backup else None,
            "validation_passed": True,
        }


def install(namespace: dict) -> None:
    """Replace Agent's direct write tool with a ticket-only proposal function."""
    original = namespace.get("tool_write")
    if not callable(original):
        raise AgentSafetyError("Agent tool_write function is unavailable.")
    if namespace.get("_MASTER_AGENT_SAFETY_INSTALLED"):
        return

    def approval_required_write(args: dict, project: Path) -> dict:
        try:
            target = namespace["safe_file"](project, args.get("path", ""))
            content = args.get("content")
            if not isinstance(content, str):
                return {"ok": False, "error": "content must be text"}
            max_bytes = int(namespace.get("CFG", {}).get("max_file_bytes", MAX_TEXT_BYTES))
            if len(content.encode("utf-8")) > min(max_bytes, MAX_TEXT_BYTES):
                return {"ok": False, "error": "File exceeds configured Agent size limit."}
            if target.suffix.lower() not in ALLOWED_EXTENSIONS:
                return {"ok": False, "error": "File extension is not enabled for editing."}
            if target.exists() and not target.is_file():
                return {"ok": False, "error": "Target is not a regular file."}
            if not target.parent.is_dir():
                return {"ok": False, "error": "Target parent directory must already exist. Agent will not create folders before approval."}

            display = namespace["display_path"](target, project)
            ticket = create_agent_ticket(
                target=target,
                selected_project=Path(project),
                display_path=display,
                proposed_content=content,
                max_bytes=max_bytes,
            )
            return {
                "ok": True,
                "status": "pending_approval",
                "approval_required": True,
                "saved": False,
                "ticket_id": ticket["ticket_id"],
                "path": ticket["relative_path"],
                "current_sha256": ticket["current_sha256"],
                "proposed_sha256": ticket["proposed_sha256"],
                "expires_at": ticket["expires_at"],
                "target_existed": ticket["target_existed"],
                "message": "No project file has been changed. Review this proposal in the local Safety Approval Center and approve the exact ticket.",
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    namespace["tool_write"] = approval_required_write
    namespace["_MASTER_AGENT_SAFETY_INSTALLED"] = True
    _audit("agent_safety_adapter_installed", {"agent_root": str(namespace.get("ROOT", ""))})


def apply_policy_authorized_ticket(ticket_id: str, policy_reason: str) -> dict:
    """Apply only a ticket admitted by integration.agent_autonomy_policy."""
    from integration.agent_autonomy_policy import evaluate
    with _LOCK:
        _, ticket = _read_ticket(ticket_id)
        if ticket.get("status") != "pending": raise AgentSafetyError("Ticket is not pending.")
        allowed, reason = evaluate(ticket.get("relative_path", ""), ticket.get("proposed_content", ""))
        if not allowed or reason != policy_reason: raise AgentSafetyError("Auto-approval policy rejected this ticket.")
        _audit("agent_policy_auto_approval", {"ticket_id": ticket_id, "path": ticket.get("relative_path"), "policy_version": "1.0", "decision": "allow", "reason": reason})
        return approve_agent_ticket(ticket_id, "APPROVE", ticket.get("current_sha256"), ticket.get("proposed_sha256"))


def rollback_applied_agent_ticket(ticket_id: str, reason: str) -> dict:
    """Rollback only if target still has the exact applied SHA256."""
    with _LOCK:
        ticket_path, ticket = _read_ticket(ticket_id)
        if ticket.get("status") != "applied": raise AgentSafetyError("Ticket is not in applied state.")
        target, _ = _resolve_ticket_target(ticket)
        applied_hash = ticket.get("applied_sha256")
        if not target.is_file() or not applied_hash or _sha_file(target) != applied_hash:
            raise AgentSafetyError("Target changed after apply; refusing rollback.")
        if ticket.get("target_existed"):
            backup_value = ticket.get("backup")
            backup_path = Path(backup_value).resolve() if backup_value else None
            if not backup_path or not _inside(backup_path, BACKUP_ROOT) or not backup_path.is_file():
                raise AgentSafetyError("Verified backup is missing or outside backup store.")
            restored = _atomic_restore(target, backup_path, applied_hash, ticket.get("current_sha256"))
        else:
            target.unlink(); restored = None
        ticket["status"] = "rolled_back"
        ticket["rollback_reason"] = str(reason)[:2000]
        ticket["proposed_content"] = ""
        _write_ticket(ticket_path, ticket)
        _audit("agent_postcheck_rollback_completed", {"ticket_id": ticket_id, "path": ticket.get("relative_path"), "reason": str(reason)[:2000], "restored_sha256": restored})
        return {"ok": True, "status": "rolled_back", "ticket_id": ticket_id, "restored_sha256": restored}

