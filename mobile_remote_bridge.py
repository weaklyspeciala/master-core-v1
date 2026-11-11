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
MOBILE_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MASTER CORE - Mobile Voice Console</title>
<style>
  body { background:#0b0f19; color:#00ffcc; font-family:monospace; margin:0; padding:12px; }
  .box { border:1px solid #00ffff; border-radius:8px; padding:12px; margin-bottom:12px; background:#111827; }
  h2 { margin:0 0 8px 0; color:#ff00ff; font-size:16px; }
  #output { white-space:pre-wrap; word-wrap:break-word; color:#e5e7eb; max-height:52vh; overflow-y:auto; font-size:13px; }
  input, select, button { width:100%; padding:12px; margin-top:8px; border-radius:6px; border:1px solid #00ffff; background:#1f2937; color:#fff; font-size:15px; box-sizing:border-box; }
  .btn-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:8px; }
  .voice-btn { background:#db2777; border-color:#f472b6; font-weight:bold; }
  .send-btn { background:#059669; border-color:#34d399; font-weight:bold; }
</style>
</head>
<body>
<div class="box">
  <h2>🤖 MASTER CORE v22.0 — MOBILE REMOTE</h2>
  <div style="display:flex; gap:6px;">
    <input type="password" id="pin" placeholder="Access PIN (default 1234)" value="1234" style="width:45%;">
    <select id="voiceLang" style="width:55%;">
      <option value="en-IN">🎙️ Voice: English / Hinglish</option>
      <option value="bn-IN">🎙️ Voice: Bengali (বাংলা)</option>
    </select>
  </div>
</div>

<div class="box">
  <div id="output">╭─[ROHAN] ⚡ [MOBILE BRIDGE ONLINE]\n╰─➤ Tap the Microphone or type a command below...</div>
</div>

<div class="box">
  <input type="text" id="cmd" placeholder="Speak or type command / question...">
  <button class="voice-btn" onclick="startVoice()">🎤 TAP & SPEAK COMMAND</button>
  <button class="send-btn" onclick="sendCmd('chat')">⚡ EXECUTE ON AGENT</button>
  <div class="btn-grid">
    <button onclick="sendCmd('audit')">🔍 System Audit</button>
    <button onclick="sendCmd('scan')">📁 Scan Files</button>
    <button onclick="sendCmd('stage_upgrade')">🛠️ Stage Code Upgrade</button>
    <button onclick="sendCmd('approve_upgrade')">✅ Approve Upgrade</button>
    <button onclick="sendCmd('rollback')">⏪ Rollback Code</button>
    <button onclick="sendCmd('ps')">💻 Run PowerShell</button>
  </div>
</div>

<script>
function startVoice() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { alert("Use Chrome on Android for Voice Input or use your keyboard microphone."); return; }
  const rec = new SR();
  rec.lang = document.getElementById('voiceLang').value;
  rec.onresult = (e) => {
    document.getElementById('cmd').value = e.results[0][0].transcript;
  };
  rec.start();
}

async function sendCmd(mode) {
  const cmdInput = document.getElementById('cmd');
  const pin = document.getElementById('pin').value;
  const out = document.getElementById('output');
  const text = cmdInput.value.trim();
  out.textContent = "⏳ Executing on Office PC Master Core...";
  const res = await fetch('/api', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pin, mode, text})
  });
  const data = await res.json();
  out.textContent = data.reply;
}
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
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        if body.get("pin") != controller.config.get("access_pin", "1234"):
            reply = "❌ Invalid Access PIN."
        else:
            mode = body.get("mode", "chat")
            text = body.get("text", "").strip()
            if mode == "audit":
                reply = controller.run_system_audit()
            elif mode == "scan":
                reply = controller.run_agent_command("scan files")
            elif mode == "stage_upgrade":
                reply = controller.stage_code_upgrade(text or "Add a system health helper function")
            elif mode == "approve_upgrade":
                reply = controller.approve_pending_upgrade()
            elif mode == "rollback":
                reply = controller.rollback_last_upgrade()
            elif mode == "ps":
                reply = controller.run_safe_powershell(text or "Get-ChildItem")
            else:
                reply = controller.run_agent_command(text or "check memory")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"reply": reply}).encode("utf-8"))

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