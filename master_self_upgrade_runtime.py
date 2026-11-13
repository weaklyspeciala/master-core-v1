"""Safe bridge from the legacy MasterSystemAgent to the existing self-development controller.
No cloud inference. All proposed edits become approval tickets; nothing is applied here.
"""
from __future__ import annotations
import os, json
from pathlib import Path

class MasterSelfUpgradeRuntime:
    def __init__(self, agent):
        self.agent = agent
        self.root = Path(agent.workspace).expanduser().resolve()
        self._controller = None

    def _tree(self, project):
        root = Path(project).resolve()
        if root != self.root:
            raise ValueError('Project root mismatch; only the configured Agent workspace is allowed.')
        rows=[]
        excluded={'.git','__pycache__','.venv','venv','node_modules','.master_dev'}
        for p in sorted(root.rglob('*')):
            try:
                rel=p.relative_to(root)
                if any(part in excluded for part in rel.parts):
                    continue
                if p.is_file(): rows.append(rel.as_posix())
                if len(rows)>=500: break
            except OSError: continue
        return '\n'.join(rows)

    def _read(self, project, relative):
        root=Path(project).resolve()
        candidate=(root / str(relative)).resolve()
        if root != self.root or (candidate != root and root not in candidate.parents):
            raise ValueError('Read blocked: path is outside configured workspace.')
        if not candidate.is_file(): raise FileNotFoundError(str(relative))
        if candidate.stat().st_size > 256_000: raise ValueError('Read blocked: file exceeds 256 KB limit.')
        return candidate.read_text(encoding='utf-8', errors='replace')

    def _write_ticket(self, args, project):
        root = Path(project).resolve()
        if root != self.root: return {"ok": False, "error": "Project root mismatch."}
        rel = str(args.get("path", "")).replace("\\", "/").strip()
        parts = [p for p in rel.split("/") if p not in ("", ".")]
        if parts and parts[0].lower() in {"master_core_v1", "master-core-v1"}: parts = parts[1:]
        rel = "/".join(parts)
        content = args.get("content")
        if not rel or not isinstance(content, str) or not content.strip(): return {"ok": False, "error": "Invalid path/content."}
        target = (root / rel).resolve()
        if target == root or root not in target.parents: return {"ok": False, "error": "Path traversal blocked."}
        try:
            from integration.agent_safety_adapter import create_agent_ticket, apply_policy_authorized_ticket, rollback_applied_agent_ticket
            from integration.agent_autonomy_policy import evaluate
            ticket = create_agent_ticket(target, root, rel, content, max_bytes=1000000)
            allowed, reason = evaluate(rel, content)
            if not allowed:
                return {"ok": True, "status": "pending_approval", "approval_required": True, "saved": False, "ticket_id": ticket["ticket_id"], "path": rel, "message": "Human approval required: " + reason}
            applied = apply_policy_authorized_ticket(ticket["ticket_id"], reason)
            if not applied.get("ok") or applied.get("status") != "validated": return applied
            import subprocess
            checks = []
            gate = self.root / "staging" / "autonomous_quality_gate.py"
            try:
                g = subprocess.run([__import__("sys").executable, str(gate)], cwd=str(self.root), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, check=False)
                checks.append(("quality_gate", g.returncode == 0, ((g.stdout or "") + (g.stderr or ""))[-10000:]))
            except Exception as exc: checks.append(("quality_gate", False, f"{type(exc).__name__}: {exc}"))
            tests = self.root / "tests"
            if tests.is_dir():
                try:
                    t = subprocess.run([__import__("sys").executable, "-m", "unittest", "discover", "-s", str(tests)], cwd=str(self.root), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, check=False)
                    checks.append(("runtime_tests", t.returncode == 0, ((t.stdout or "") + (t.stderr or ""))[-10000:]))
                except Exception as exc: checks.append(("runtime_tests", False, f"{type(exc).__name__}: {exc}"))
            else: checks.append(("runtime_tests", None, "No tests/ directory; runtime suite not configured."))
            failed = [c for c in checks if c[1] is False]
            if failed:
                why = "\n".join(f"{n}: {out}" for n, _, out in failed)
                try:
                    rolled = rollback_applied_agent_ticket(ticket["ticket_id"], why)
                    return {"ok": False, "status": "rolled_back", "ticket_id": ticket["ticket_id"], "path": rel, "post_change_checks": checks, "rollback": rolled, "message": "Post-change check failed; verified rollback completed."}
                except Exception as exc:
                    return {"ok": False, "status": "recovery_required", "ticket_id": ticket["ticket_id"], "path": rel, "post_change_checks": checks, "rollback_error": f"{type(exc).__name__}: {exc}"}
            return {"ok": True, "status": "validated", "approval_required": False, "saved": True, "ticket_id": ticket["ticket_id"], "path": rel, "post_change_checks": checks, "message": "Applied and post-change checks passed."}
        except Exception as exc:
            return {"ok": False, "status": "blocked", "error": f"{type(exc).__name__}: {exc}"}

    def _local_model(self, messages):
        # llama.cpp server OpenAI-compatible endpoint. No remote fallback.
        import requests
        url=os.environ.get('MASTER_LOCAL_LLM_URL','http://127.0.0.1:8080/v1/chat/completions')
        model=os.environ.get('MASTER_LOCAL_LLM_MODEL','/data/data/com.termux/files/home/MASTER_AI_MOBILE/local_brain/models/qwen2.5-1.5b-instruct-q4_k_m.gguf')
        response=requests.post(url, json={'model':model,'messages':messages,'temperature':0.2}, timeout=180)
        response.raise_for_status()
        data=response.json()
        return {'content':data['choices'][0]['message']['content']}

    def _search_disabled(self, query):
        return 'Web research is disabled in this offline-first self-upgrade bridge. Complete local reasoning and safety validation first.'

    def run(self, objective):
        if not objective.strip(): return {'status':'error','message':'Task description is empty.'}
        if self._controller is None:
            from staging.self_development_controller_v1 import SelfDevelopmentController
            callbacks={
                'tool_tree': self._tree,
                'tool_read': self._read,
                'tool_write': self._write_ticket,
                'ollama': self._local_model,
                'tool_search': self._search_disabled,
            }
            self._controller=SelfDevelopmentController(callbacks, str(self.root))
        try:
            return self._controller.execute_development_task(objective)
        except Exception as exc:
            return {'status':'error','message':f'{type(exc).__name__}: {exc}'}
    def list_pending_tickets(self):
        # List pending Agent-edit tickets without applying them.
        from integration import agent_safety_adapter as adapter
        items = []
        if not adapter.APPROVAL_ROOT.is_dir():
            return {"ok": True, "tickets": []}
        for ticket_path in sorted(adapter.APPROVAL_ROOT.glob("*.json")):
            try:
                ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
                if ticket.get("ticket_kind") == "agent_project_edit" and ticket.get("status") == "pending":
                    items.append({
                        "ticket_id": ticket.get("ticket_id"),
                        "path": ticket.get("relative_path"),
                        "expires_at": ticket.get("expires_at"),
                        "current_sha256": ticket.get("current_sha256"),
                        "proposed_sha256": ticket.get("proposed_sha256"),
                    })
            except (OSError, ValueError, TypeError):
                continue
        return {"ok": True, "tickets": items}

    def approval_preview(self, ticket_id):
        # Return proposal details for human review; does not apply changes.
        from integration.agent_safety_adapter import _read_ticket
        _, ticket = _read_ticket(ticket_id)
        if ticket.get("status") != "pending":
            return {"ok": False, "status": ticket.get("status"), "error": "Ticket is not pending."}
        return {
            "ok": True, "status": "pending_approval",
            "ticket_id": ticket.get("ticket_id"), "path": ticket.get("relative_path"),
            "expires_at": ticket.get("expires_at"),
            "current_sha256": ticket.get("current_sha256"),
            "proposed_sha256": ticket.get("proposed_sha256"),
            "proposed_content": ticket.get("proposed_content", ""),
        }

    def approve_ticket(self, ticket_id, typed_confirmation):
        # Apply one ticket only after exact typed human confirmation.
        if typed_confirmation != "APPROVE":
            return {"ok": False, "status": "not_approved",
                    "error": "Confirmation must be exactly APPROVE."}
        from integration.agent_safety_adapter import _read_ticket, approve_agent_ticket
        _, ticket = _read_ticket(ticket_id)
        return approve_agent_ticket(
            ticket_id=ticket_id,
            typed_confirmation=typed_confirmation,
            expected_current_sha256=ticket.get("current_sha256"),
            expected_proposed_sha256=ticket.get("proposed_sha256"),
        )

