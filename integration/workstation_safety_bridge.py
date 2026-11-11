"""Safe write integration bridge for MASTER AI WORKSTATION.

This module is installed by Phase 3 Step 6.
It intercepts existing-file update tool calls and /api/write requests.
Writes require a short-lived content-hash-bound approval ticket.
Approval runs static validation; failed validation triggers guarded rollback.
The dashboard approval API is localhost-only and checks browser Origin.
"""
from __future__ import annotations

import ipaddress
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


_INSTALLED = False
TICKET_ID_RE = re.compile(r"^[0-9a-fA-F-]{32,36}$")
MAX_API_BODY = 2 * 1024 * 1024


def _ticket_record(sfo, ticket_id):
    if not isinstance(ticket_id, str) or not TICKET_ID_RE.fullmatch(ticket_id):
        raise sfo.SafetyError("Invalid approval ticket ID.")
    ticket_path = (sfo.APPROVAL_ROOT / (ticket_id + ".json")).resolve()
    try:
        ticket_path.relative_to(sfo.APPROVAL_ROOT.resolve())
    except ValueError:
        raise sfo.SafetyError("Ticket path is outside the approval store.")
    if not ticket_path.is_file():
        raise sfo.SafetyError("Approval ticket not found.")
    return json.loads(ticket_path.read_text(encoding="utf-8"))


def _public_ticket(ticket):
    return {
        "ticket_id": ticket.get("ticket_id"),
        "relative_path": ticket.get("relative_path"),
        "current_sha256": ticket.get("current_sha256"),
        "proposed_sha256": ticket.get("proposed_sha256"),
        "created_at": ticket.get("created_at"),
        "expires_at": ticket.get("expires_at"),
        "status": ticket.get("status"),
    }


def _validate_edited_file(path: Path, max_bytes: int) -> bool:
    """Static validation only: no project file is imported or executed."""
    try:
        raw = path.read_bytes()
        if len(raw) > max_bytes:
            return False
        text = raw.decode("utf-8")
        suffix = path.suffix.lower()
        if suffix == ".py":
            compile(text, str(path), "exec")
        elif suffix == ".json":
            json.loads(text)
        return True
    except (OSError, UnicodeDecodeError, SyntaxError, json.JSONDecodeError, ValueError):
        return False


def _local_origin_allowed(handler) -> bool:
    """Allow only loopback clients and same-origin browser writes."""
    try:
        peer = ipaddress.ip_address(handler.client_address[0])
        if not peer.is_loopback:
            return False

        host_header = str(handler.headers.get("Host", "")).strip()
        host_parts = urlparse("//" + host_header)
        if host_parts.hostname not in {"127.0.0.1", "localhost", "::1"}:
            return False
        if host_parts.port != int(handler.server.server_port):
            return False

        origin = handler.headers.get("Origin")
        if origin:
            parsed = urlparse(origin)
            if parsed.scheme != "http":
                return False
            if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                return False
            if parsed.port != int(handler.server.server_port):
                return False
            if parsed.netloc.lower() != host_header.lower():
                return False
        return True
    except Exception:
        return False


def _read_json_body(handler):
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except (TypeError, ValueError):
        raise ValueError("Invalid Content-Length.")
    if length <= 0 or length > MAX_API_BODY:
        raise ValueError("Request body is empty or exceeds the 2 MB API limit.")
    raw = handler.rfile.read(length)
    if len(raw) != length:
        raise ValueError("Incomplete request body.")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON request body must be an object.")
    return data


def _send(handler, status, data):
    handler.send_json(status, data)


def install(namespace: dict) -> None:
    """Install the bridge into workstation.py runtime globals."""
    global _INSTALLED
    if _INSTALLED:
        return

    required = ("ROOT", "WORKSPACE", "Handler", "TOOL_FUNCTIONS", "safe_workspace_path")
    missing = [name for name in required if name not in namespace]
    if missing:
        raise RuntimeError("Safe bridge could not install; missing workstation symbols: " + ", ".join(missing))

    root = Path(namespace["ROOT"]).resolve()
    workspace = Path(namespace["WORKSPACE"]).resolve()
    core = root / "MASTER_CORE_V1"
    safety_dir = core / "safety"
    integration_dir = core / "integration"
    if not safety_dir.is_dir() or not integration_dir.is_dir():
        raise RuntimeError("MASTER_CORE_V1 safety/integration folders are missing.")
    sys.path.insert(0, str(safety_dir))
    import safe_file_ops as sfo
    import recovery_ops as recovery

    safe_workspace_root = Path(sfo.WORKSPACE_ROOT).resolve()
    try:
        workspace.relative_to(safe_workspace_root)
    except ValueError:
        raise RuntimeError("Workstation workspace is outside the protected safe_file_ops workspace.")

    max_bytes = int(namespace.get("MAX_TEXT_BYTES", 1024 * 1024))

    def safe_tool_update(args):
        try:
            relative = str(args.get("path", "")).strip()
            target = namespace["safe_workspace_path"](relative)
            if not target.is_file():
                return {"ok": False, "error": "Existing file not found. This approval bridge currently handles edits to existing files only."}
            if target.stat().st_size > max_bytes:
                return {"ok": False, "error": "File exceeds the configured text size limit."}
            try:
                target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return {"ok": False, "error": "File is not UTF-8 text."}
            content, repaired = namespace["validate_python_source"](target, args.get("content", ""))
            relative = target.resolve().relative_to(safe_workspace_root).as_posix()
            ticket = sfo.create_approval_ticket(relative, content)
            return {
                "ok": True,
                "status": "pending_approval",
                "saved": False,
                "approval_required": True,
                "ticket_id": ticket["ticket_id"],
                "path": relative,
                "current_sha256": ticket["current_sha256"],
                "proposed_sha256": ticket["proposed_sha256"],
                "expires_at": ticket["expires_at"],
                "newline_repair_applied": repaired,
                "message": "No file change has been made. Review the proposed content and approve this exact ticket before it is applied.",
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    namespace["tool_update"] = safe_tool_update
    namespace["TOOL_FUNCTIONS"]["update_workspace_file"] = safe_tool_update

    handler_class = namespace["Handler"]
    original_post = handler_class.do_POST
    original_get = handler_class.do_GET

    def _pending_items():
        items = []
        for item in sorted(sfo.APPROVAL_ROOT.glob("*.json")):
            try:
                ticket = json.loads(item.read_text(encoding="utf-8"))
                if ticket.get("status") == "pending":
                    items.append(_public_ticket(ticket))
            except Exception:
                continue
        return items

    def wrapped_post(self):
        parsed = urlparse(self.path)
        route = parsed.path
        if route not in {"/api/write", "/api/safety/approve", "/api/safety/reject"}:
            return original_post(self)

        if not _local_origin_allowed(self):
            return _send(self, 403, {"ok": False, "error": "Blocked: request must be same-origin and loopback-only."})

        try:
            data = _read_json_body(self)

            if route == "/api/write":
                result = safe_tool_update(data)
                if result.get("approval_required"):
                    # ok=False prevents legacy UI code from claiming the file was saved.
                    return _send(self, 202, {**result, "ok": False})
                return _send(self, 400, result)

            ticket_id = data.get("ticket_id")
            ticket = _ticket_record(sfo, ticket_id)

            if route == "/api/safety/reject":
                result = sfo.reject_approval(ticket_id)
                return _send(self, 200, result)

            expected_current = data.get("expected_current_sha256")
            expected_proposed = data.get("expected_proposed_sha256")
            if expected_current != ticket.get("current_sha256"):
                return _send(self, 409, {"ok": False, "error": "Current-file hash does not match the reviewed ticket."})
            if expected_proposed != ticket.get("proposed_sha256"):
                return _send(self, 409, {"ok": False, "error": "Proposed-content hash does not match the reviewed ticket."})

            typed_confirmation = data.get("typed_confirmation", "")
            if typed_confirmation != "APPROVE":
                return _send(self, 400, {"ok": False, "error": "Type exactly APPROVE to apply this ticket."})

            if ticket.get("ticket_kind") == "agent_project_edit":
                from agent_safety_adapter_v2 import approve_agent_ticket, AgentSafetyError
                try:
                    result = approve_agent_ticket(
                        ticket_id,
                        typed_confirmation,
                        expected_current,
                        expected_proposed,
                    )
                except AgentSafetyError as exc:
                    return _send(self, 409, {"ok": False, "error": str(exc)})
                if result.get("status") == "validated":
                    return _send(self, 200, result)
                if result.get("status") == "rolled_back":
                    return _send(self, 422, result)
                return _send(self, 409, result)
            result = recovery.approve_apply_and_validate(
                ticket_id,
                typed_confirmation,
                lambda path: _validate_edited_file(path, max_bytes),
            )
            if result.get("status") == "validated":
                return _send(self, 200, result)
            if result.get("status") == "rolled_back":
                return _send(self, 422, result)
            return _send(self, 409, result)

        except (ValueError, json.JSONDecodeError, sfo.SafetyError) as exc:
            return _send(self, 400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            return _send(self, 500, {"ok": False, "error": f"Safe bridge error: {type(exc).__name__}: {exc}"})

    def wrapped_get(self):
        parsed = urlparse(self.path)
        if parsed.path == "/safety":
            from approval_panel import render_panel
            return self.send_data(200, render_panel(), "text/html; charset=utf-8")
        if parsed.path not in {"/api/safety/pending", "/api/safety/ticket"}:
            return original_get(self)
        if not _local_origin_allowed(self):
            return _send(self, 403, {"ok": False, "error": "Loopback-only endpoint."})
        try:
            if parsed.path == "/api/safety/pending":
                return _send(self, 200, {"ok": True, "tickets": _pending_items()})
            from urllib.parse import parse_qs
            query = parse_qs(parsed.query)
            ticket_id = query.get("ticket_id", [""])[0]
            ticket = _ticket_record(sfo, ticket_id)
            # Return the proposal to the local dashboard for human review.
            visible = dict(_public_ticket(ticket))
            visible["proposed_content"] = ticket.get("proposed_content", "")
            return _send(self, 200, {"ok": True, "ticket": visible})
        except Exception as exc:
            return _send(self, 400, {"ok": False, "error": str(exc)})

    handler_class.do_POST = wrapped_post
    handler_class.do_GET = wrapped_get
    _INSTALLED = True