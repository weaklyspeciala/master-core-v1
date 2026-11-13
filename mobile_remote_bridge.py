import os
import sys
import io
import re
import time
import json
import shutil
import socket
import datetime
import py_compile
import subprocess
import threading
import contextlib
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

# Ensure workspace is in sys.path and import existing untouched agent
WORKSPACE = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from master_studio_agent import MasterSystemAgent, BROWSER_HEADERS

BACKUP_DIR = os.path.join(WORKSPACE, "backups")
CONFIG_FILE = os.path.join(WORKSPACE, "mobile_bridge_config.json")
STAGING_FILE = os.path.join(WORKSPACE, "_staging_upgrade_test.py")

os.makedirs(BACKUP_DIR, exist_ok=True)

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

def strip_ansi(text):
    return ANSI_ESCAPE.sub('', text)

class SafeMobileController:
    def __init__(self):
        # Initialize the existing agent using the current workspace dynamically
        self.agent = MasterSystemAgent(workspace=WORKSPACE)
        self.lock = threading.Lock()
        self.pending_upgrade = None
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        default_cfg = {
            "telegram_bot_token": "",
            "authorized_chat_id": "",
            "web_port": 8080,
            "access_pin": "1234"
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_cfg, f, indent=2)
        return default_cfg

    def run_agent_command(self, prompt):
        """Runs any command through the existing MasterSystemAgent without modifying it."""
        with self.lock:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                try:
                    self.agent.chat_response(prompt)
                except Exception as e:
                    print(f"Execution Error: {e}")
            raw_output = buffer.getvalue()
            # Also print to the Office PC console so PC workflow stays visible
            sys.__stdout__.write(raw_output)
            sys.__stdout__.flush()
            return strip_ansi(raw_output).strip()

    def run_system_audit(self):
        """Checks syntax health, backups, memory count, and disk status."""
        agent_file = os.path.join(WORKSPACE, "master_studio_agent.py")
        audit_lines = [
            "🔍 MASTER CORE SYSTEM AUDIT",
            f"• Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"• Active Agent Version: {getattr(self.agent, 'version', 'Unknown')}",
            f"• Active Language: {self.agent.current_language.upper()}",
            f"• Learned Topics in DB: {len(self.agent.memory_db)}"
        ]
        try:
            py_compile.compile(agent_file, doraise=True)
            audit_lines.append("• Syntax Check (master_studio_agent.py): ✅ PASSED (0 Errors)")
        except Exception as e:
            audit_lines.append(f"• Syntax Check: ❌ FAILED ({e})")

        backups = sorted(os.listdir(BACKUP_DIR)) if os.path.exists(BACKUP_DIR) else []
        audit_lines.append(f"• Saved Safety Backups: {len(backups)}")
        if backups:
            audit_lines.append(f"• Latest Backup: {backups[-1]}")
        return "\n".join(audit_lines)

    def stage_code_upgrade(self, instruction):
        """Uses the AI Brain to generate a new helper module or patch and validates syntax."""
        system_msg = (
            "You are an expert Python developer upgrading Rohan's Master Autonomous Agent. "
            "Write clean, standalone Python code or functions fulfilling the user's request. "
            "Return ONLY valid Python code without markdown fences."
        )
        payload = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"Write a Python module/function for: {instruction}"}
            ]
        }
        headers = dict(BROWSER_HEADERS)
        headers["Content-Type"] = "application/json"
        resp = requests.post("https://text.pollinations.ai/openai", json=payload, headers=headers, timeout=25)
        code = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        code = re.sub(r"^```python\s*|```$", "", code, flags=re.MULTILINE).strip()

        with open(STAGING_FILE, "w", encoding="utf-8") as f:
            f.write(code + "\n")

        try:
            py_compile.compile(STAGING_FILE, doraise=True)
            self.pending_upgrade = {
                "instruction": instruction,
                "code": code,
                "timestamp": datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            }
            return (
                "✅ STAGED & SYNTAX VERIFIED!\n\n"
                f"Task: {instruction}\n\n"
                "--- PREVIEW ---\n"
                f"{code[:600]}\n"
                "---------------\n"
                "Reply or tap 'APPROVE UPGRADE' to save and activate, or 'REJECT' to cancel."
            )
        except Exception as e:
            return f"❌ SYNTAX AUDIT FAILED (Blocked automatically for safety):\n{e}"

    def approve_pending_upgrade(self):
        if not self.pending_upgrade:
            return "ℹ️ No pending upgrade in staging."
        ts = self.pending_upgrade["timestamp"]
        ext_file = os.path.join(WORKSPACE, "agent_custom_extensions.py")
        if os.path.exists(ext_file):
            shutil.copy2(ext_file, os.path.join(BACKUP_DIR, f"agent_custom_extensions_{ts}.py.bak"))

        with open(ext_file, "a", encoding="utf-8") as f:
            f.write(f"\n\n# === UPGRADE [{ts}]: {self.pending_upgrade['instruction']} ===\n")
            f.write(self.pending_upgrade["code"] + "\n")

        self.pending_upgrade = None
        return f"🚀 UPGRADE APPLIED SAFELY!\nSaved to: agent_custom_extensions.py (Backup stored in /backups)."

    def rollback_last_upgrade(self):
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".bak")])
        if not backups:
            return "ℹ️ No backups found to roll back."
        latest = backups[-1]
        src = os.path.join(BACKUP_DIR, latest)
        target = os.path.join(WORKSPACE, "agent_custom_extensions.py")
        shutil.copy2(src, target)
        return f"⏪ ROLLBACK COMPLETE: Restored {latest} safely."

    def run_safe_powershell(self, cmd):
        blocked = ["remove-item", "del ", "rm ", "format-", "stop-computer", "restart-computer"]
        if any(b in cmd.lower() for b in blocked):
            return "🛡️ SAFETY GUARD: Destructive PowerShell commands are blocked remotely."
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                cwd=WORKSPACE,
                capture_output=True,
                text=True,
                timeout=15
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            return out.strip()[:1500] or "✅ Command executed (no output)."
        except Exception as e:
            return f"❌ PowerShell Error: {e}"

controller = SafeMobileController()

# =====================================================================
# MOBILE VOICE WEB CONSOLE (Works on Android Chrome via Wi-Fi / Tailscale)
# =====================================================================
MOBILE_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#10131b">
<title>MASTER CORE | Command Workspace</title>
<style>
:root {
  color-scheme: dark;
  --bg:#10131b;
  --panel:#191e29;
  --panel2:#202737;
  --line:#30394b;
  --text:#edf1fa;
  --muted:#9aa7bc;
  --accent:#78aaff;
  --green:#65d6a0;
  --red:#ff8585;
  --yellow:#f1c879;
}
* { box-sizing:border-box; }
body {
  margin:0;
  background:var(--bg);
  color:var(--text);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
  line-height:1.5;
}
main {
  width:min(100%,850px);
  margin:auto;
  padding:22px 16px 40px;
}
header {
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:12px;
  margin-bottom:22px;
}
.brand { font-size:19px; font-weight:750; letter-spacing:.4px; }
.sub { color:var(--muted); font-size:12px; }
.status {
  border:1px solid var(--line);
  border-radius:30px;
  padding:6px 11px;
  color:var(--muted);
  font-size:12px;
  white-space:nowrap;
}
.status.running { color:var(--yellow); }
.status.completed { color:var(--green); }
.status.error { color:var(--red); }
.panel {
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:15px;
  padding:16px;
  margin-bottom:15px;
}
h1 { font-size:21px; margin:0 0 5px; }
h2 { font-size:15px; margin:0 0 12px; }
.muted { color:var(--muted); font-size:13px; }
textarea, input {
  display:block;
  width:100%;
  border:1px solid var(--line);
  border-radius:10px;
  background:#111722;
  color:var(--text);
  padding:13px;
  font:14px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace;
  outline:none;
}
textarea:focus, input:focus {
  border-color:var(--accent);
}
#cmd {
  min-height:190px;
  max-height:55vh;
  resize:vertical;
  overflow:auto;
  overflow-wrap:anywhere;
  white-space:pre-wrap;
}
#pin { margin-top:10px; }
.row {
  display:flex;
  flex-wrap:wrap;
  gap:9px;
  margin-top:12px;
}
button {
  border:1px solid var(--line);
  border-radius:10px;
  background:var(--panel2);
  color:var(--text);
  padding:11px 15px;
  font-weight:650;
  font-size:13px;
  cursor:pointer;
}
button:disabled { opacity:.45; cursor:not-allowed; }
.primary {
  background:#315f9e;
  border-color:#477fc5;
}
.danger { color:#ffb0a9; }
#review { display:none; }
.review-text {
  white-space:pre-wrap;
  overflow-wrap:anywhere;
  max-height:45vh;
  overflow:auto;
  padding:13px;
  background:#111722;
  border:1px solid var(--line);
  border-radius:10px;
  font:13px/1.6 ui-monospace,monospace;
}
#output {
  white-space:normal;
  overflow-wrap:anywhere;
  font-size:14px;
}
#output pre {
  margin:12px 0;
  padding:13px;
  border:1px solid var(--line);
  border-radius:10px;
  background:#0c111a;
  overflow-x:auto;
  white-space:pre;
  font:13px/1.6 ui-monospace,monospace;
}
#output code { font-family:ui-monospace,monospace; }
#output p { margin:9px 0; }
#output h1,#output h2,#output h3 { margin:15px 0 7px; }
#output ul { padding-left:22px; }
details summary {
  cursor:pointer;
  color:var(--accent);
  font-weight:650;
}
.tools {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:9px;
  margin-top:14px;
}
.tools button { width:100%; }
@media(max-width:430px) {
  main { padding:16px 12px 30px; }
  .panel { padding:13px; }
  .tools { grid-template-columns:1fr 1fr; }
}
</style>
</head>
<body>
<main>
<header>
  <div>
    <div class="brand">MASTER CORE</div>
    <div class="sub">Mobile Command Workspace</div>
  </div>
  <div id="status" class="status">IDLE</div>
</header>

<section class="panel">
  <h1>Command Workspace</h1>
  <div class="muted">Write your task, review it, then explicitly approve execution.</div>
  <textarea id="cmd" spellcheck="false"
    placeholder="Describe what you want MASTER CORE to do..."></textarea>
  <div class="row" style="justify-content:space-between;align-items:center">
    <span class="muted" id="count">0 characters</span>
    <button type="button" id="voice">🎙 Voice input</button>
  </div>
  <input id="pin" type="password" autocomplete="current-password"
    placeholder="Access PIN">
  <div class="row">
    <button class="primary" id="reviewButton" type="button">Review task</button>
    <button type="button" id="clearButton">Clear editor</button>
  </div>
  <div class="muted" id="message" aria-live="polite"></div>
</section>

<section class="panel" id="review">
  <h2>Review before execution</h2>
  <div class="muted">Read the complete task below. Nothing has been executed yet.</div>
  <div class="review-text" id="reviewText"></div>
  <div class="row">
    <button type="button" id="backButton">Back to edit</button>
    <button type="button" class="primary" id="approveButton">Approve &amp; Execute</button>
  </div>
</section>

<section class="panel">
  <h2>Agent response</h2>
  <div class="muted" id="outputHint">Responses will appear here.</div>
  <div id="output" aria-live="polite"></div>
</section>

<section class="panel">
  <details>
    <summary>Additional tools</summary>
    <div class="muted" style="margin-top:10px">
      Utility actions require a separate confirmation.
    </div>
    <div class="tools">
      <button data-mode="audit">System audit</button>
      <button data-mode="scan">Scan files</button>
      <button data-mode="stage_upgrade">Stage upgrade</button>
      <button data-mode="approve_upgrade">Approve upgrade</button>
      <button data-mode="rollback" class="danger">Rollback</button>
      <button data-mode="ps">Safe PowerShell</button>
    </div>
  </details>
</section>
</main>

<script>
(() => {
  const $ = id => document.getElementById(id);
  const cmd = $("cmd");
  let busy = false;

  function setStatus(value) {
    $("status").textContent = value.toUpperCase();
    $("status").className = "status " + value;
  }

  function updateCount() {
    $("count").textContent = cmd.value.length.toLocaleString() + " characters";
  }

  function showMessage(value) {
    $("message").textContent = value;
  }

  function renderResponse(raw) {
    const root = $("output");
    root.replaceChildren();
    const source = String(raw ?? "");
    const lines = source.split(/\r?\n/);
    let paragraph = [];
    let list = null;
    let code = null;
    let codeLines = [];

    function flushParagraph() {
      if (!paragraph.length) return;
      const p = document.createElement("p");
      p.textContent = paragraph.join(" ");
      root.appendChild(p);
      paragraph = [];
    }
    function flushList() {
      if (list) root.appendChild(list);
      list = null;
    }
    function flushCode() {
      const pre = document.createElement("pre");
      const el = document.createElement("code");
      el.textContent = codeLines.join("\n");
      pre.appendChild(el);
      root.appendChild(pre);
      codeLines = [];
    }

    for (const line of lines) {
      if (line.trim().startsWith("```")) {
        flushParagraph();
        flushList();
        if (code) {
          flushCode();
          code = null;
        } else {
          code = true;
        }
        continue;
      }
      if (code) {
        codeLines.push(line);
        continue;
      }
      const heading = line.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        flushParagraph();
        flushList();
        const h = document.createElement("h" + heading[1].length);
        h.textContent = heading[2];
        root.appendChild(h);
      } else if (/^\s*[-*]\s+/.test(line)) {
        flushParagraph();
        if (!list) list = document.createElement("ul");
        const li = document.createElement("li");
        li.textContent = line.replace(/^\s*[-*]\s+/, "");
        list.appendChild(li);
      } else if (!line.trim()) {
        flushParagraph();
        flushList();
      } else {
        flushList();
        paragraph.push(line);
      }
    }
    if (code) flushCode();
    flushParagraph();
    flushList();
    $("outputHint").textContent = source ? "Latest agent response" : "No response text.";
  }

  async function post(mode, approved, confirmed) {
    if (busy) return;
    const pin = $("pin").value;
    const text = cmd.value;

    if (!pin) {
      showMessage("Enter your Access PIN first.");
      return;
    }
    if ((mode === "chat" || mode === "stage_upgrade" || mode === "ps") &&
        !text.trim()) {
      showMessage("Enter a task or command first.");
      return;
    }

    busy = true;
    $("approveButton").disabled = true;
    $("reviewButton").disabled = true;
    setStatus("running");
    showMessage("MASTER CORE is processing your request...");

    try {
      const response = await fetch("/api", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          pin, mode, text,
          approved: approved === true,
          confirmed: confirmed === true
        })
      });
      const data = await response.json();
      if (!response.ok || data.ok === false) {
        throw new Error(data.error || data.reply || ("HTTP " + response.status));
      }
      renderResponse(data.reply);
      setStatus("completed");
      showMessage("Request completed.");
      if (mode === "chat") $("review").style.display = "none";
    } catch (error) {
      setStatus("error");
      showMessage(error.message || "Request failed.");
      renderResponse("ERROR: " + (error.message || "Request failed."));
    } finally {
      busy = false;
      $("approveButton").disabled = false;
      $("reviewButton").disabled = false;
    }
  }

  cmd.addEventListener("input", updateCount);
  $("clearButton").addEventListener("click", () => {
    if (busy) return;
    cmd.value = "";
    updateCount();
    $("review").style.display = "none";
    showMessage("Editor cleared.");
    cmd.focus();
  });

  $("reviewButton").addEventListener("click", () => {
    if (busy) return;
    if (!cmd.value.trim()) {
      showMessage("Write a task before reviewing.");
      return;
    }
    $("reviewText").textContent = cmd.value;
    $("review").style.display = "block";
    setStatus("reviewing");
    showMessage("Review the full task. Execution has not started.");
    $("review").scrollIntoView({behavior:"smooth", block:"start"});
  });

  $("backButton").addEventListener("click", () => {
    $("review").style.display = "none";
    setStatus("idle");
    cmd.focus();
  });

  $("approveButton").addEventListener("click", () => {
    if (!confirm("You are approving this task for execution. Continue?")) return;
    post("chat", true, false);
  });

  document.querySelectorAll("[data-mode]").forEach(button => {
    button.addEventListener("click", () => {
      const mode = button.dataset.mode;
      const labels = {
        audit:"Run system audit?",
        scan:"Scan project files?",
        stage_upgrade:"Stage an upgrade using the editor content?",
        approve_upgrade:"Approve the pending upgrade?",
        rollback:"Run rollback?",
        ps:"Run the safe PowerShell command in the editor?"
      };
      if (!confirm(labels[mode] + "\n\nContinue only if you understand this action.")) return;
      post(mode, false, true);
    });
  });

  $("voice").addEventListener("click", () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      showMessage("Voice recognition is not supported by this browser.");
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.onresult = event => {
      const spoken = event.results[0][0].transcript;
      cmd.value += (cmd.value ? "\n" : "") + spoken;
      updateCount();
      showMessage("Voice text added to the editor. Review it before execution.");
    };
    recognition.onerror = event => showMessage("Voice input: " + event.error);
    recognition.start();
    showMessage("Listening... Your speech will only fill the editor.");
  });

  cmd.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      const start = cmd.selectionStart;
      const end = cmd.selectionEnd;
      cmd.setRangeText("\n", start, end, "end");
      updateCount();
    }
  });

  updateCount();
})();
</script>
</body>
</html>
"""


class MobileWebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(MOBILE_HTML.encode("utf-8"))

    def do_POST(self):
        import json

        def send_json(status, payload):
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        try:
            raw_length = self.headers.get("Content-Length", "0")
            try:
                length = int(raw_length)
            except (TypeError, ValueError):
                return send_json(400, {"ok": False, "error": "Invalid Content-Length."})

            if length < 0:
                return send_json(400, {"ok": False, "error": "Invalid request length."})
            if length > 2 * 1024 * 1024:
                return send_json(413, {"ok": False, "error": "Request is too large."})

            raw_body = self.rfile.read(length)
            if len(raw_body) != length:
                return send_json(400, {"ok": False, "error": "Incomplete request body."})

            try:
                body = json.loads(raw_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return send_json(400, {"ok": False, "error": "Invalid JSON or UTF-8 request."})

            if not isinstance(body, dict):
                return send_json(400, {"ok": False, "error": "Request must be a JSON object."})

            expected_pin = str(controller.config.get("access_pin", "1234"))
            supplied_pin = body.get("pin")
            if not isinstance(supplied_pin, str) or supplied_pin != expected_pin:
                return send_json(403, {"ok": False, "error": "Invalid Access PIN."})

            mode = body.get("mode", "chat")
            if not isinstance(mode, str):
                return send_json(400, {"ok": False, "error": "Invalid mode."})

            allowed_modes = {
                "chat", "audit", "scan", "stage_upgrade",
                "approve_upgrade", "rollback", "ps"
            }
            if mode not in allowed_modes:
                return send_json(400, {"ok": False, "error": "Unsupported mode."})

            text = body.get("text", "")
            if not isinstance(text, str):
                return send_json(400, {"ok": False, "error": "Prompt must be text."})

            if len(text.encode("utf-8")) > 1024 * 1024:
                return send_json(413, {"ok": False, "error": "Prompt exceeds the 1 MiB limit."})

            if mode == "chat":
                if body.get("approved") is not True:
                    return send_json(403, {
                        "ok": False,
                        "error": "Execution blocked. Review the prompt and explicitly approve it first."
                    })
                if not text.strip():
                    return send_json(400, {"ok": False, "error": "Prompt is empty."})
                reply = controller.run_agent_command(text)

            else:
                if body.get("confirmed") is not True:
                    return send_json(403, {
                        "ok": False,
                        "error": "Utility action requires explicit confirmation."
                    })

                if mode == "audit":
                    reply = controller.run_system_audit()
                elif mode == "scan":
                    reply = controller.run_agent_command("scan files")
                elif mode == "stage_upgrade":
                    reply = controller.stage_code_upgrade(
                        text if text.strip() else "Add a system health helper function"
                    )
                elif mode == "approve_upgrade":
                    reply = controller.approve_pending_upgrade()
                elif mode == "rollback":
                    reply = controller.rollback_last_upgrade()
                elif mode == "ps":
                    reply = controller.run_safe_powershell(
                        text if text.strip() else "Get-ChildItem"
                    )

            return send_json(200, {"ok": True, "reply": str(reply)})

        except Exception as exc:
            return send_json(500, {
                "ok": False,
                "error": "Server error: " + str(exc)
            })

def telegram_polling_loop():
    token = controller.config.get("telegram_bot_token", "").strip()
    if not token:
        return
    print(f"\033[38;5;46m[TELEGRAM BRIDGE] Online! Listening for mobile commands...\033[0m")
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=20"
            resp = requests.get(url, timeout=25).json()
            for item in resp.get("result", []):
                offset = item["update_id"] + 1
                msg = item.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "").strip()
                if not text:
                    continue

                auth_id = str(controller.config.get("authorized_chat_id", "")).strip()
                if auth_id and chat_id != auth_id:
                    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": "⛔ Unauthorized device."})
                    continue

                if text.lower() in ["/start", "menu"]:
                    reply = (
                        f"🤖 MASTER CORE v22.0 MOBILE BRIDGE\n"
                        f"Your Chat ID: {chat_id}\n\n"
                        "Commands:\n"
                        "• Send any question/command directly\n"
                        "• /audit — Run System & Syntax Audit\n"
                        "• /upgrade <task> — Stage & Verify Code Upgrade\n"
                        "• /approve — Apply Staged Upgrade\n"
                        "• /rollback — Undo Last Upgrade\n"
                        "• /ps <cmd> — Run Safe PowerShell"
                    )
                elif text.lower() == "/audit":
                    reply = controller.run_system_audit()
                elif text.lower().startswith("/upgrade "):
                    reply = controller.stage_code_upgrade(text[9:].strip())
                elif text.lower() == "/approve":
                    reply = controller.approve_pending_upgrade()
                elif text.lower() == "/rollback":
                    reply = controller.rollback_last_upgrade()
                elif text.lower().startswith("/ps "):
                    reply = controller.run_safe_powershell(text[4:].strip())
                else:
                    reply = controller.run_agent_command(text)

                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": reply[:4000]}
                )
        except Exception:
            time.sleep(3)

if __name__ == "__main__":
    port = int(controller.config.get("web_port", 8080))
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print("\033[38;5;51m" + "═" * 78 + "\033[0m")
    print("\033[38;5;226m 📱 MASTER CORE SIDECAR — MOBILE VOICE & REMOTE BRIDGE ONLINE\033[0m")
    print(f"\033[38;5;46m 🌐 Android Web Voice Console : http://{local_ip}:{port} (PIN: {controller.config.get('access_pin')})\033[0m")
    print(f"\033[38;5;248m ⚙️ Config File               : {CONFIG_FILE}\033[0m")
    print("\033[38;5;51m" + "═" * 78 + "\033[0m\n")

    threading.Thread(target=telegram_polling_loop, daemon=True).start()
    server = HTTPServer(("0.0.0.0", port), MobileWebHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\033[38;5;196m[STOP] Mobile Remote Bridge stopped safely.\033[0m")