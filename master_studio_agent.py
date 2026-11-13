import os
import sys
import time
import datetime
import warnings
import json
import textwrap
import webbrowser
import re
import urllib.parse

warnings.filterwarnings("ignore")

import requests
from bs4 import BeautifulSoup
import questionary
from questionary import Style
import shutil

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

class MasterSystemAgent:
    def __init__(self, workspace=None):
        if workspace is None:
            workspace = os.environ.get(
                "MASTER_CORE_WORKSPACE",
                os.path.dirname(os.path.abspath(__file__))
            )
        self.workspace = os.path.abspath(os.path.expanduser(workspace))
        self.evolution_log = os.path.join(self.workspace, "evolution_history.log")
        self.memory_db_file = os.path.join(self.workspace, "knowledge_base.json")
        self.version = "v22.0-MultiCoreAIBrain"
        self.current_language = "english"
        self.active_intel = "Initialized with 4-Core AI Brain + Deep Webpage Reader."

        if not os.path.exists(self.workspace):
            os.makedirs(self.workspace)

        self.memory_db = self.load_memory_db()
        self.load_latest_intel()

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def load_memory_db(self):
        if os.path.exists(self.memory_db_file):
            try:
                with open(self.memory_db_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_to_memory(self, query, answer):
        key = query.lower().strip()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.memory_db[key] = {
            "timestamp": timestamp,
            "answer": answer
        }
        try:
            with open(self.memory_db_file, "w", encoding="utf-8") as f:
                json.dump(self.memory_db, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        summary_line = answer.replace("\n", " ")[:120]
        self.active_intel = f"[{timestamp}] Q: '{query}' -> {summary_line}..."
        with open(self.evolution_log, "a", encoding="utf-8") as f:
            f.write(self.active_intel + "\n")

    def load_latest_intel(self):
        if os.path.exists(self.evolution_log):
            try:
                with open(self.evolution_log, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        self.active_intel = lines[-1].strip()
            except Exception:
                pass

    def print_banner(self):
        self.clear_screen()
        import shutil

        width = max(36, min(shutil.get_terminal_size((80, 20)).columns, 88))
        inner = width - 2
        cyan = "\033[38;5;51m"
        blue = "\033[38;5;39m"
        white = "\033[38;5;255m"
        muted = "\033[38;5;245m"
        green = "\033[38;5;46m"
        yellow = "\033[38;5;226m"
        reset = "\033[0m"

        def row(label, value, color=white):
            content = f"  {label:<11} {value}"
            content = content[:inner].ljust(inner)
            print(f"{cyan}│{muted}{content[:13]}{color}{content[13:]}{cyan}│{reset}")

        print(f"{cyan}╭{'━' * inner}╮{reset}")
        title = "MASTER CORE"
        subtitle = "AUTONOMOUS ReAct AGENT  •  MULTI-CORE AI"
        print(f"{cyan}│{reset}{yellow}{title.center(inner)}{reset}{cyan}│{reset}")
        print(f"{cyan}│{reset}{blue}{subtitle[:inner].center(inner)}{reset}{cyan}│{reset}")
        print(f"{cyan}├{'─' * inner}┤{reset}")

        row("SYSTEM", "ONLINE", green)
        row("WORKSPACE", self.workspace, white)
        row("AI ENGINE", "LOCAL QWEN / AVAILABLE TOOLS", blue)
        row("MEMORY", "READY", green)
        row("LANGUAGE", self.current_language.upper(), yellow)

        print(f"{cyan}╰{'━' * inner}╯{reset}\n")

    def print_agent_activity(self, phase, detail):
        """Update the single live spinner status without duplicate log lines."""
        with MASTER_ACTIVITY_LOCK:
            MASTER_ACTIVITY_STATE["phase"] = str(phase)
            MASTER_ACTIVITY_STATE["detail"] = str(detail)

    def print_agent_box(self, title, message, color_code="\033[38;5;51m", text_color="\033[38;5;255m"):
        import shutil

        width = max(36, min(shutil.get_terminal_size((80, 20)).columns, 88))
        inner = width - 2
        clean_title = str(title).strip()
        available = max(20, inner - 4)

        heading = f" {clean_title} "
        heading = heading[:max(1, inner - 2)]
        remaining = max(0, inner - len(heading) - 1)

        print(
            f"{color_code}╭─{heading}"
            f"{'─' * remaining}╮\033[0m"
        )

        for paragraph in str(message).split("\n"):
            clean = (
                paragraph.replace("**", "")
                .replace("### ", "◆ ")
                .replace("## ", "▸ ")
            )

            if not clean.strip():
                print(f"{color_code}│\033[0m")
                continue

            for line in textwrap.wrap(
                clean,
                width=available,
                break_long_words=True,
                break_on_hyphens=False
            ):
                print(f"{color_code}│ {text_color}{line:<{available}}\033[0m{color_code} │\033[0m")

        print(f"{color_code}╰{'─' * inner}╯\033[0m\n")

    def set_language(self, lang):
        lang_l = lang.lower()
        if "bengali" in lang_l or "বাংলা" in lang_l:
            self.current_language = "bengali"
        elif "hinglish" in lang_l:
            self.current_language = "hinglish"
        else:
            self.current_language = "english"
        self.print_banner()
        self.print_agent_box("🌐 LANGUAGE UPDATED", f"Active response language set to: {self.current_language.upper()}", "\033[38;5;46m")

    def execute_os_task(self, command):
        # Workspace-confined file operations; never overwrite existing files.
        from pathlib import Path
        import tempfile
        import hashlib

        root = Path(self.workspace).resolve()
        text = command.strip()
        lowered = text.lower()

        def resolve_inside(name):
            candidate = (root / name).resolve()
            if candidate == root or root not in candidate.parents:
                raise ValueError("Path must stay inside the configured workspace.")
            return candidate

        if any(word in lowered for word in ("scan", "list", "show files")):
            self.print_agent_activity("SCANNING FILES", "Listing workspace entries...")
            try:
                files = sorted(p.name for p in root.iterdir())[:30]
                self.print_agent_box("FILE SYSTEM", "Workspace files:\\n" + "\\n".join(files), "\\033[38;5;226m")
            except Exception as exc:
                self.print_agent_box("FILE SCAN FAILED", str(exc), "\\033[38;5;196m")
            return

        if lowered.startswith("read "):
            self.print_agent_activity("READING FILE", "Checking the requested workspace file...")
            name = text[5:].strip().strip('"').strip("'")
            try:
                target = resolve_inside(name)
                if not target.is_file():
                    raise FileNotFoundError(name)
                content = target.read_text(encoding="utf-8", errors="replace")
                self.print_agent_box("READ: " + target.name, content[:4000], "\\033[38;5;46m")
            except Exception as exc:
                self.print_agent_box("SAFE READ BLOCKED", str(exc), "\\033[38;5;196m")
            return

        if any(word in lowered for word in ("create", "write", "make file")):
            self.print_agent_activity("CREATING FILE", "Preparing a new file safely...")
            name = "autonomous_script.py" if "python" in lowered else "agent_notes.txt"
            try:
                target = resolve_inside(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    self.print_agent_box("OVERWRITE BLOCKED", name + " already exists. No file changed.", "\\033[38;5;196m")
                    return
                content = "# Generated by Master Agent\\n# Command: " + text.replace("\\n", " ") + "\\nprint('New file created successfully.')\\n"
                fd, temp_name = tempfile.mkstemp(prefix=".master_new_", dir=str(target.parent))
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as handle:
                        handle.write(content)
                        handle.flush()
                        os.fsync(handle.fileno())
                    if target.exists():
                        raise FileExistsError("Target appeared during write; stopped.")
                    os.replace(temp_name, target)
                finally:
                    try:
                        os.unlink(temp_name)
                    except OSError:
                        pass
                file_hash = hashlib.sha256(target.read_bytes()).hexdigest()
                self.print_agent_box("NEW FILE CREATED", "Path: " + str(target) + "\\nSHA-256: " + file_hash, "\\033[38;5;46m")
            except Exception as exc:
                self.print_agent_box("SAFE WRITE FAILED", str(exc), "\\033[38;5;196m")
            return

        self.print_agent_box("TASK NOT RECOGNIZED", "Use: scan files | read filename | create a file", "\\033[38;5;226m")

    def fetch_live_web_context(self, query):
        snippets = []
        urls = []
        if any(w in query.lower() for w in ["trending", "news", "today", "headlines"]):
            try:
                resp = requests.get("https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en", headers=BROWSER_HEADERS, timeout=6)
                titles = re.findall(r"<title>(.*?)</title>", resp.text)
                for t in titles[2:8]:
                    snippets.append(f"- {t}")
            except Exception:
                pass

        if DDGS_AVAILABLE and not snippets:
            try:
                search_q = query
                if query.lower().startswith("how to"):
                    search_q = f"{query} step by step tutorial guide -book -novel -shop"
                with DDGS() as ddgs:
                    results = list(ddgs.text(search_q, region="us-en", safesearch="moderate", max_results=5))
                    for r in results:
                        body = r.get("body", "").strip()
                        title = r.get("title", "").strip()
                        href = r.get("href", "").strip()
                        if body and not any(spam in body.lower() for spam in ["airfare", "coupon", "flight booking", "one-stop shop", "graphic novel"]):
                            snippets.append(f"- {title}: {body}")
                            if href:
                                urls.append(href)
            except Exception:
                pass

        return "\n".join(snippets[:4]), urls

    def deep_read_webpage(self, urls):
        """Fallback Core 4: Reads actual step-by-step paragraphs from the top tutorial URL."""
        for url in urls[:2]:
            try:
                resp = requests.get(url, headers=BROWSER_HEADERS, timeout=8)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()

                extracted = []
                for elem in soup.find_all(["h2", "h3", "p", "li"]):
                    txt = elem.get_text(" ", strip=True)
                    if len(txt) > 35 and not any(j in txt.lower() for j in ["cookie", "privacy policy", "subscribe", "sign in"]):
                        if elem.name in ["h2", "h3"]:
                            extracted.append(f"\n🔹 {txt}")
                        else:
                            extracted.append(f"  • {txt[:220]}")
                    if len(extracted) >= 10:
                        break
                if len(extracted) >= 4:
                    return f"Extracted directly from {url}:\n" + "\n".join(extracted)
            except Exception:
                continue
        return ""

    def ask_ai_llm_brain(self, user_prompt, web_context=""):
        """Stream the real AI answer word by word into the terminal."""
        import os
        import json
        import requests
        import sys
        import time
        import re
        import shutil

        global MASTER_LIVE_STREAM_RENDERED
        MASTER_LIVE_STREAM_RENDERED = False

        endpoint = os.environ.get(
            "MASTER_LOCAL_LLM_URL",
            "http://127.0.0.1:8080/v1/chat/completions"
        )
        prompt = str(user_prompt).strip()
        if web_context:
            prompt += "\n\nLocal context:\n" + str(web_context)

        payload = {
            "model": os.environ.get("MASTER_LOCAL_LLM_MODEL", "/data/data/com.termux/files/home/MASTER_AI_MOBILE/local_brain/models/qwen2.5-1.5b-instruct-q4_k_m.gguf"),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the offline reasoning brain of MASTER CORE V1. "
                        "Give accurate, practical answers. Never claim to have "
                        "changed files or executed commands unless confirmed."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "stream": True
        }

        self.print_agent_activity(
            "CONNECTING TO LOCAL AI",
            "Connecting..."
        )

        parts = []
        pending_word = ""
        first_chunk = True
        line_width = 0
        line_open = False
        content_width = max(24, shutil.get_terminal_size((80, 20)).columns - 6)

        color = "\033[38;5;46m"
        text_color = "\033[38;5;253m"
        stream = sys.stdout

        def new_line():
            nonlocal line_width, line_open
            stream.write("\n")
            stream.flush()
            line_width = 0
            line_open = False

        def render_word(raw_word):
            nonlocal line_width, line_open

            word = (
                raw_word.replace("**", "")
                .replace("__", "")
                .replace("~~", "")
                .replace("`", "")
            )

            if not word:
                return

            # Remove standalone Markdown heading markers.
            if re.fullmatch(r"#{1,6}", word):
                return

            if line_width and line_width + len(word) > content_width:
                new_line()

            if not line_open:
                stream.write(f"{color}│{text_color} ")
                line_open = True

            stream.write(word)
            line_width += len(word)
            stream.flush()

            # Real word-by-word typing delay.
            if word.endswith((".", "!", "?", ";", ":")):
                time.sleep(0.075)
            elif word.endswith((",",)):
                time.sleep(0.045)
            else:
                time.sleep(0.030)

        def render_piece(piece):
            nonlocal pending_word, line_width, line_open

            for char in piece:
                if char.isspace():
                    if pending_word:
                        render_word(pending_word)
                        pending_word = ""

                    if char == "\n":
                        new_line()
                    elif char == "\t":
                        if line_width < content_width:
                            stream.write("    ")
                            line_width += 4
                    elif line_open and line_width < content_width:
                        stream.write(" ")
                        line_width += 1
                    stream.flush()
                else:
                    pending_word += char

        with requests.post(
            endpoint,
            json=payload,
            stream=True,
            timeout=(10, 180)
        ) as response:
            response.raise_for_status()

            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue

                if isinstance(raw_line, bytes):
                    raw_line = raw_line.decode("utf-8", errors="replace")

                raw_line = raw_line.strip()

                if raw_line.startswith(":"):
                    continue

                data = (
                    raw_line[5:].strip()
                    if raw_line.startswith("data:")
                    else raw_line
                )

                if data == "[DONE]":
                    break

                if not data.startswith("{"):
                    continue

                try:
                    packet = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choices = packet.get("choices") or []
                if not choices:
                    continue

                choice = choices[0]
                delta = choice.get("delta") or {}
                piece = delta.get("content")

                if piece is None:
                    piece = choice.get("text")

                if piece is None:
                    piece = (choice.get("message") or {}).get("content")

                if isinstance(piece, str) and piece:
                    if first_chunk:
                        first_chunk = False
                        MASTER_LIVE_STREAM_RENDERED = True

                        with MASTER_ACTIVITY_LOCK:
                            MASTER_ACTIVITY_STATE["phase"] = "LIVE RESPONSE"
                            MASTER_ACTIVITY_STATE["detail"] = "Typing answer..."

                        stream.write(
                            f"\n{color}╭─[ 🟢 LIVE RESPONSE / OUTPUT ] "
                            f"──────────────────────────────────────\033[0m\n"
                        )
                        stream.flush()

                    parts.append(piece)
                    render_piece(piece)

        if pending_word:
            render_word(pending_word)
            pending_word = ""

        answer = "".join(parts).strip()

        if not answer:
            raise RuntimeError(
                "Local AI streaming completed without a response. "
                "Check the local server's streaming support."
            )

        if line_open:
            new_line()

        stream.write(
            f"{color}╰──────────────────────────────────────────────────────────────────────────────"
            f"\033[0m\n\n"
        )
        stream.flush()
        self.print_agent_activity(
            "RESPONSE RECEIVED",
            "Answer generation completed."
        )
        return answer

    def superpower_brain_search(self, user_prompt):
        """Offline-first streamed answer path with existing memory behavior."""
        global MASTER_LIVE_STREAM_RENDERED

        clean = user_prompt.strip()
        print("\033[38;5;226m╭─[ 🧠 MASTER AI ENGINE ] ────────────────────────────────────────────────\033[0m")
        self.print_agent_activity(
            "AI PROCESSING",
            "Waiting for the configured AI engine..."
        )

        try:
            answer = self.ask_ai_llm_brain(clean)
        except Exception as exc:
            self.print_agent_activity("AI ERROR", f"{type(exc).__name__}: {exc}")
            answer = f"Local AI core unavailable: {type(exc).__name__}: {exc}"

        unavailable = (
            "no local language model is configured" in answer.lower()
            or answer.lower().startswith("local ai core unavailable:")
            or "could not reach online sources" in answer.lower()
        )

        if not unavailable:
            self.print_agent_activity(
                "SAVING MEMORY",
                "Saving the completed answer to the knowledge base..."
            )
            self.save_to_memory(clean, answer)
            footer = (
                f"(💾 Saved to knowledge_base.json | "
                f"Total learned topics: {len(self.memory_db)})"
            )
        else:
            footer = "(ℹ️ Not saved: local AI reasoning is not configured.)"

        if MASTER_LIVE_STREAM_RENDERED:
            print(
                f"\033[38;5;46m│\033[38;5;248m {footer}\033[0m"
            )
            print(
                "\033[38;5;46m╰──────────────────────────────────────────────────────────────────────────────\033[0m\n"
            )
        else:
            print("\033[38;5;226m╰──────────────────────────────────────────────────────────────────────\033[0m\n")
            self.print_agent_box(
                "🤖 MASTER AGENT",
                answer + "\n\n" + footer,
                "\033[38;5;46m",
                "\033[38;5;253m"
            )

    def run_self_upgrade(self, objective):
        """Run the guarded self-upgrade controller; edits require separate approval."""
        try:
            from master_self_upgrade_runtime import MasterSelfUpgradeRuntime
            runtime = getattr(self, "_master_self_upgrade_runtime", None)
            if runtime is None:
                runtime = MasterSelfUpgradeRuntime(self)
                self._master_self_upgrade_runtime = runtime
            result = runtime.run(objective)
            self.print_agent_box("SELF-UPGRADE RESULT", str(result), "\033[38;5;46m")
            return result
        except Exception as exc:
            message = f"Self-upgrade unavailable: {type(exc).__name__}: {exc}"
            self.print_agent_box("SELF-UPGRADE BLOCKED", message, "\033[38;5;196m")
            return {"status": "blocked", "message": message}

    def chat_response(self, user_prompt):
        # MASTER CORE AUTONOMOUS SUPERPOWER DISPATCH
        try:
            from autonomous_superpower_engine import dispatch
            if dispatch(self, user_prompt):
                return
        except Exception as exc:
            print('\033[91m[AUTONOMOUS ENGINE ERROR] '
                  + type(exc).__name__ + ': ' + str(exc) + '\033[0m')
            print('\033[94m[INFO] Returning to existing agent routing.\033[0m')
        prompt_lower = user_prompt.lower().strip()
        self.print_agent_activity("REQUEST RECEIVED", "Reading your instruction...")
        self.print_agent_box(
            "📝 PROMPT / INPUT",
            user_prompt,
            "\033[38;5;208m",
            "\033[38;5;253m"
        )

        if prompt_lower.startswith("open ") and not any(w in prompt_lower for w in ["search", "type", "result", "how", "what", "why", "who"]):
            target = prompt_lower.replace("open", "").strip()
            self.print_agent_box("🚀 SYSTEM EXECUTION", f"Opening '{target}' in your browser...", "\033[38;5;46m")
            clean_target = target.replace(" ", "")
            if "chatgpt" in clean_target:
                webbrowser.open("https://chatgpt.com")
            elif "youtube" in clean_target:
                webbrowser.open("https://youtube.com")
            elif "github" in clean_target:
                webbrowser.open("https://github.com")
            else:
                webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(target)}")

        elif any(w in prompt_lower for w in ["scan files", "list files", "show files", "read ", "create a file", "write a file"]):
            self.print_agent_activity("FILE TASK", "Routing to the existing workspace file handler...")
            self.execute_os_task(user_prompt)

        elif prompt_lower.startswith(("upgrade:", "develop:", "self-upgrade:")):
            objective = user_prompt.split(":", 1)[1].strip()
            if objective:
                self.run_self_upgrade(objective)
            else:
                self.print_agent_box("SELF-UPGRADE", "Use: upgrade: describe the improvement you want.", "\033[38;5;226m")
        elif prompt_lower == "pending-upgrades":
            try:
                from master_self_upgrade_runtime import MasterSelfUpgradeRuntime
                runtime = getattr(self, "_master_self_upgrade_runtime", None)
                if runtime is None:
                    runtime = MasterSelfUpgradeRuntime(self)
                    self._master_self_upgrade_runtime = runtime
                tickets = runtime.list_pending_tickets().get("tickets", [])
                if tickets:
                    lines = []
                    for item in tickets:
                        lines.append(
                            f"Ticket: {item.get('ticket_id')}\nPath: {item.get('path')}\n"
                            f"Expires: {item.get('expires_at')}\n"
                            f"Current SHA256: {item.get('current_sha256')}\n"
                            f"Proposed SHA256: {item.get('proposed_sha256')}"
                        )
                    self.print_agent_box("PENDING APPROVAL TICKETS", "\n\n".join(lines), "\033[38;5;226m")
                else:
                    self.print_agent_box("PENDING APPROVAL TICKETS", "No pending self-upgrade tickets found.", "\033[38;5;46m")
            except Exception as exc:
                self.print_agent_box("APPROVAL LIST FAILED", f"{type(exc).__name__}: {exc}", "\033[38;5;196m")

        elif prompt_lower.startswith("approve:"):
            ticket_id = user_prompt.split(":", 1)[1].strip()
            try:
                if not ticket_id:
                    raise ValueError("Use: approve: <ticket-id>")
                from master_self_upgrade_runtime import MasterSelfUpgradeRuntime
                runtime = getattr(self, "_master_self_upgrade_runtime", None)
                if runtime is None:
                    runtime = MasterSelfUpgradeRuntime(self)
                    self._master_self_upgrade_runtime = runtime
                preview = runtime.approval_preview(ticket_id)
                if not preview.get("ok"):
                    raise ValueError(preview.get("error", "Ticket is not approvable."))
                self.print_agent_box(
                    "REVIEW PROPOSED FILE CHANGE",
                    f"Ticket: {ticket_id}\nPath: {preview.get('path')}\n"
                    f"Current SHA256: {preview.get('current_sha256')}\n"
                    f"Proposed SHA256: {preview.get('proposed_sha256')}\n\n"
                    f"PROPOSED CONTENT:\n{preview.get('proposed_content', '')[:12000]}",
                    "\033[38;5;226m"
                )
                confirmation = input("Type exactly APPROVE to apply this ticket: ").strip()
                result = runtime.approve_ticket(ticket_id, confirmation)
                color = "\033[38;5;46m" if result.get("ok") else "\033[38;5;196m"
                self.print_agent_box("APPROVAL RESULT", str(result), color)
            except Exception as exc:
                self.print_agent_box("APPROVAL BLOCKED", f"{type(exc).__name__}: {exc}", "\033[38;5;196m")

        elif prompt_lower.startswith(("search:", "web search:", "অনলাইনে খোঁজো:", "সার্চ:")):
            self.print_agent_activity("WEB SEARCH", "Starting the existing search workflow...")
            query = user_prompt.split(":", 1)[1].strip()
            if not query:
                self.print_agent_box("WEB SEARCH", "Write a query after search: (example: search: latest Unity 6 news).", "\\033[38;5;226m")
            else:
                snippets, urls = self.fetch_live_web_context(query)
                if snippets:
                    page_notes = self.deep_read_webpage(urls) if urls else ""
                    combined = snippets + ("\\n\\n" + page_notes if page_notes else "")
                    self.print_agent_box("SUPERPOWER WEB SEARCH", combined, "\\033[38;5;46m")
                elif not DDGS_AVAILABLE:
                    self.print_agent_box("WEB SEARCH NOT READY", "Install search dependency in Termux: pip install ddgs", "\\033[38;5;226m")
                else:
                    self.print_agent_box("WEB SEARCH", "No results. Check internet or try another query.", "\\033[38;5;196m")

        elif any(w in prompt_lower for w in ["what did you learn", "check memory", "show memory"]):
            mem_count = len(self.memory_db)
            recent_keys = list(self.memory_db.keys())[-5:]
            topics_str = "\n".join([f" • {k}" for k in recent_keys]) if recent_keys else " • No topics saved yet."
            msg = f"Total Learned Topics in Database: {mem_count}\n\nRecent Topics:\n{topics_str}\n\nLatest Log:\n{self.active_intel}"
            self.print_agent_box("🧠 AGENT MEMORY DATABASE", msg, "\033[38;5;198m")

        else:
            self.print_agent_activity("BRAIN THINKING", "Sending your prompt to the configured AI engine...")
            self.superpower_brain_search(user_prompt)



def collect_and_confirm_prompt(agent, label):
    """Collect multiline prompt and require explicit SEND confirmation."""
    sentinel = ":SEND"

    while True:
        print(f"\033[38;5;51m{label}\033[0m")
        print("Paste or type your instruction.")
        print(f"Finish by entering {sentinel} on a separate line.")
        print("Your task will NOT run until you select SEND.\n")

        lines = []
        try:
            while True:
                line = input("\033[38;5;46m│ \033[0m")
                if line.strip() == sentinel:
                    break
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            print("\nInput cancelled. Nothing was sent.")
            return None

        prompt = "\n".join(lines).strip()
        if not prompt:
            print("Empty prompt. Nothing was sent.")
            return None

        agent.print_agent_box(
            "PROMPT REVIEW — CHECK BEFORE SENDING",
            prompt,
            "\033[38;5;226m"
        )

        choice = questionary.select(
            "Send this instruction to MASTER CORE?",
            choices=[
                "➤ SEND — Submit this prompt",
                "✏️ EDIT — Enter the prompt again",
                "✖ CANCEL — Do not send"
            ],
            style=cli_style,
            pointer="➤"
        ).ask()

        if choice == "➤ SEND — Submit this prompt":
            return prompt

        if choice == "✏️ EDIT — Enter the prompt again":
            continue

        agent.print_agent_box(
            "SEND CANCELLED",
            "No task was submitted or executed.",
            "\033[38;5;226m"
        )
        return None


cli_style = Style([
    ('qmark', 'fg:#00ffff bold'),
    ('question', 'fg:#ffffff bold'),
    ('answer', 'fg:#00ff00 bold'),
    ('pointer', 'fg:#ff00ff bold'),
    ('selected', 'fg:#00ff00 bold'),
])


MASTER_ACTIVITY_STATE = {"phase": "IDLE", "detail": "Ready", "started_at": 0.0}
MASTER_ACTIVITY_LOCK = __import__("threading").RLock()


MASTER_LIVE_STREAM_RENDERED = False


def run_with_smooth_spinner(label, callback):
    """Display one compact status line until answer typing begins."""
    import sys
    import threading
    import time

    result = {}
    errors = []
    finished = threading.Event()

    with MASTER_ACTIVITY_LOCK:
        MASTER_ACTIVITY_STATE["phase"] = label
        MASTER_ACTIVITY_STATE["detail"] = "Starting"
        MASTER_ACTIVITY_STATE["started_at"] = time.monotonic()

    class LiveOutput:
        def __init__(self, original):
            self.original = original
            self.owner = None

        def write(self, value):
            if threading.current_thread() is self.owner:
                self.original.write(value)
                self.original.flush()
                return len(value)
            return self.original.write(value)

        def flush(self):
            self.original.flush()

        def __getattr__(self, name):
            return getattr(self.original, name)

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    stdout_proxy = LiveOutput(original_stdout)
    stderr_proxy = LiveOutput(original_stderr)

    def worker():
        try:
            result["value"] = callback()
        except Exception as exc:
            errors.append(exc)
        finally:
            finished.set()

    thread = threading.Thread(target=worker, daemon=True)
    stdout_proxy.owner = thread
    stderr_proxy.owner = thread

    frames = ("◐", "◓", "◑", "◒")
    index = 0

    try:
        sys.stdout = stdout_proxy
        sys.stderr = stderr_proxy
        thread.start()

        while not finished.is_set():
            with MASTER_ACTIVITY_LOCK:
                phase = MASTER_ACTIVITY_STATE["phase"]
                started = MASTER_ACTIVITY_STATE.get(
                    "started_at", time.monotonic()
                )

            if phase != "LIVE RESPONSE":
                elapsed = max(0.0, time.monotonic() - started)
                frame = frames[index % len(frames)]

                # Keep the status short enough to fit on one terminal row.
                short_phase = str(phase)[:25]
                original_stdout.write(
                    f"\r\033[2K\033[38;5;51m{frame}\033[0m "
                    f"\033[1m{short_phase}\033[0m "
                    f"\033[38;5;248m{elapsed:.1f}s\033[0m"
                )
                original_stdout.flush()
                index += 1

            finished.wait(0.12)

    finally:
        if thread.ident is not None:
            thread.join()
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        original_stdout.write("\r\033[2K")
        original_stdout.flush()

    if errors:
        exc = errors[0]
        original_stdout.write(
            f"\nMASTER CORE ERROR: {type(exc).__name__}: {exc}\n"
        )
        original_stdout.flush()

    with MASTER_ACTIVITY_LOCK:
        MASTER_ACTIVITY_STATE["phase"] = (
            "COMPLETED" if not errors else "FAILED"
        )
        MASTER_ACTIVITY_STATE["detail"] = "Task finished"

    return result.get("value")

if __name__ == "__main__":
    agent = MasterSystemAgent()
    agent.print_banner()

    agent.print_agent_box(
        "UNIVERSAL INTERFACE",
        "One prompt. One agent brain. One continuous response area.\n"
        "Type any instruction and press ENTER to execute.\n"
        "Type EXIT to safely stop MASTER CORE.",
        "\033[38;5;46m",
        "\033[38;5;255m"
    )

    while True:
        try:
            prompt_color = "\033[38;5;51m"
            reset_color = "\033[0m"

            terminal_width = max(
                36, shutil.get_terminal_size((80, 20)).columns
            )
            prompt_inner = terminal_width - 2
            prompt_heading = "─[ MASTER PROMPT ] "
            prompt_top = (
                "╭" + prompt_heading
                + "─" * max(0, prompt_inner - len(prompt_heading))
                + "╮"
            )

            print(f"\n{prompt_color}{prompt_top}{reset_color}")
            user_input = input(
                f"{prompt_color}╰─➤ {reset_color}"
            ).strip()

            if not user_input:
                continue

            if user_input.upper() in {":EXIT", "EXIT"}:
                agent.print_agent_box(
                    "SYSTEM HALT",
                    "MASTER CORE safely stopped.",
                    "\033[38;5;196m"
                )
                break

            print("")
            run_with_smooth_spinner(
                "MASTER CORE THINKING",
                lambda: agent.chat_response(user_input)
            )
            print("")

        except KeyboardInterrupt:
            print("\n")
            agent.print_agent_box(
                "SYSTEM HALT",
                "Agent safely stopped.",
                "\033[38;5;196m"
            )
            break

