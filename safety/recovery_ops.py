"""Controlled automatic rollback helpers for MASTER_CORE_V1.

This module does not replace safe_file_ops.py. It wraps its approved-write
operation and restores a verified backup if a post-write validator fails.

Safety properties:
- Requires an existing, approved ticket and exact APPROVE confirmation.
- Uses only backup files inside safe_file_ops.BACKUP_ROOT.
- Verifies the backup against the ticket's original SHA256.
- Restores only if the target still has the exact post-apply SHA256.
- Rechecks the target immediately before atomic replacement.
- Preserves the backup and refuses to overwrite concurrent changes.
- Does not delete files or run validation commands itself. A caller supplies
  a validator callable that must return the boolean True for success.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Callable, Any

try:
    from . import safe_file_ops as _sfo
except ImportError:
    import safe_file_ops as _sfo


class RecoveryError(_sfo.SafetyError):
    """Raised when a verified rollback cannot safely be completed."""


def _contained(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def _load_applied_ticket(ticket_id: str) -> dict:
    ticket_path = (_sfo.APPROVAL_ROOT / (ticket_id + ".json")).resolve()
    if not _contained(ticket_path, _sfo.APPROVAL_ROOT) or not ticket_path.is_file():
        raise RecoveryError("Approval ticket not found inside the approval store.")
    try:
        ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RecoveryError(f"Approval ticket could not be read: {exc}") from exc
    if ticket.get("ticket_id") != ticket_id or ticket.get("status") != "applied":
        raise RecoveryError("Ticket must be successfully applied before validation rollback.")
    return ticket


def _verified_backup(ticket: dict, applied: dict) -> Path:
    backup_value = applied.get("backup")
    if not isinstance(backup_value, str) or not backup_value.strip():
        raise RecoveryError("Approved-write result did not provide a backup path.")
    backup = Path(backup_value).resolve()
    if not _contained(backup, _sfo.BACKUP_ROOT) or not backup.is_file():
        raise RecoveryError("Backup is missing or is outside the protected backup directory.")
    expected_original_hash = ticket.get("current_sha256")
    actual_backup_hash = _sfo.sha256_file(backup)
    if not expected_original_hash or actual_backup_hash != expected_original_hash:
        raise RecoveryError("Backup SHA256 does not match the ticket's original file hash.")
    return backup


def _restore_verified_backup(
    relative_path: str,
    backup: Path,
    expected_current_hash: str,
    expected_backup_hash: str,
) -> dict:
    target = _sfo.safe_target(relative_path)
    if not target.is_file():
        raise RecoveryError("Rollback target no longer exists.")
    if _sfo.sha256_file(backup) != expected_backup_hash:
        raise RecoveryError("Backup changed after verification; rollback refused.")
    if _sfo.sha256_file(target) != expected_current_hash:
        raise RecoveryError(
            "Target changed after the approved edit; rollback refused to avoid overwriting newer changes."
        )

    backup_bytes = backup.read_bytes()
    staged_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=str(target.parent),
            prefix=".mastercore_rollback_",
            suffix=".tmp",
        ) as staged:
            staged_name = staged.name
            staged.write(backup_bytes)
            staged.flush()
            os.fsync(staged.fileno())

        staged_path = Path(staged_name)
        if _sfo.sha256_file(staged_path) != expected_backup_hash:
            raise RecoveryError("Staged recovery file failed SHA256 verification.")

        # Re-resolve and recheck immediately before replacement.
        target = _sfo.safe_target(relative_path)
        if not target.is_file() or _sfo.sha256_file(target) != expected_current_hash:
            raise RecoveryError(
                "Target changed immediately before rollback; newer content was not overwritten."
            )
        if _sfo.sha256_file(backup) != expected_backup_hash:
            raise RecoveryError("Backup changed immediately before rollback.")

        os.replace(str(staged_path), str(target))
        staged_name = None

        restored_hash = _sfo.sha256_file(target)
        if restored_hash != expected_backup_hash:
            raise RecoveryError(
                "Post-rollback SHA256 mismatch. Preserve the backup and inspect the target manually."
            )
        return {
            "restored_path": str(target),
            "backup_path": str(backup),
            "restored_sha256": restored_hash,
        }
    finally:
        if staged_name and os.path.exists(staged_name):
            try:
                os.unlink(staged_name)
            except OSError:
                pass


def approve_apply_and_validate(
    ticket_id: str,
    typed_confirmation: str,
    validator: Callable[[Path], bool],
) -> dict:
    """Apply one approved ticket, validate the result, and roll back on failure.

    The validator receives the edited Path and must return exactly True.
    False or an exception triggers a guarded restore from the verified backup.
    If the target changed after the edit, rollback is refused and the backup
    remains available for manual recovery.
    """
    if not callable(validator):
        raise RecoveryError("validator must be a callable that accepts the target Path.")

    applied = _sfo.approve_and_apply(ticket_id, typed_confirmation)
    if applied.get("ok") is not True or applied.get("status") != "applied":
        raise RecoveryError("The approved write did not report a successful applied status.")

    ticket = _load_applied_ticket(ticket_id)
    relative_path = applied.get("path")
    if relative_path != ticket.get("relative_path"):
        raise RecoveryError("Applied path does not match the approved ticket.")

    target = _sfo.safe_target(relative_path)
    expected_applied_hash = applied.get("sha256")
    if not isinstance(expected_applied_hash, str) or _sfo.sha256_file(target) != expected_applied_hash:
        raise RecoveryError("Applied target hash does not match the approved-write result.")

    backup = _verified_backup(ticket, applied)
    validation_error = None
    try:
        validation_result = validator(target)
        validation_passed = validation_result is True
        if not validation_passed:
            validation_error = "Validator did not return the boolean True."
    except Exception as exc:
        validation_passed = False
        validation_error = f"{type(exc).__name__}: {exc}"

    if validation_passed:
        _sfo._audit("post_edit_validation_passed", {
            "ticket_id": ticket_id,
            "path": relative_path,
            "sha256": expected_applied_hash,
        })
        return {
            "ok": True,
            "status": "validated",
            "ticket_id": ticket_id,
            "path": relative_path,
            "sha256": expected_applied_hash,
            "backup": str(backup),
            "validation_passed": True,
        }

    try:
        restored = _restore_verified_backup(
            relative_path=relative_path,
            backup=backup,
            expected_current_hash=expected_applied_hash,
            expected_backup_hash=ticket["current_sha256"],
        )
        _sfo._audit("automatic_rollback_completed", {
            "ticket_id": ticket_id,
            "path": relative_path,
            "backup": str(backup),
            "restored_sha256": restored["restored_sha256"],
            "validation_error": validation_error,
        })
        return {
            "ok": False,
            "status": "rolled_back",
            "ticket_id": ticket_id,
            "path": relative_path,
            "backup": str(backup),
            "validation_passed": False,
            "validation_error": validation_error,
            **restored,
        }
    except Exception as exc:
        _sfo._audit("automatic_rollback_refused_or_failed", {
            "ticket_id": ticket_id,
            "path": relative_path,
            "backup": str(backup),
            "validation_error": validation_error,
            "recovery_error": f"{type(exc).__name__}: {exc}",
        })
        return {
            "ok": False,
            "status": "recovery_required",
            "ticket_id": ticket_id,
            "path": relative_path,
            "backup": str(backup),
            "validation_passed": False,
            "validation_error": validation_error,
            "recovery_error": f"{type(exc).__name__}: {exc}",
        }


def restore_verified_backup(
    relative_path: str,
    backup_path: str,
    expected_current_sha256: str,
    expected_backup_sha256: str,
) -> dict:
    """Manually request a guarded restore using both caller-supplied hashes."""
    if not isinstance(backup_path, str) or not backup_path.strip():
        raise RecoveryError("A backup path is required.")
    backup = Path(backup_path).resolve()
    if not _contained(backup, _sfo.BACKUP_ROOT) or not backup.is_file():
        raise RecoveryError("Backup is missing or is outside the protected backup directory.")
    if _sfo.sha256_file(backup) != expected_backup_sha256:
        raise RecoveryError("Backup hash does not match the expected SHA256.")
    result = _restore_verified_backup(
        relative_path=relative_path,
        backup=backup,
        expected_current_hash=expected_current_sha256,
        expected_backup_hash=expected_backup_sha256,
    )
    _sfo._audit("manual_verified_restore_completed", {
        "path": relative_path,
        "backup": str(backup),
        "restored_sha256": result["restored_sha256"],
    })
    return result