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
    def __init__(self, workspace=r"H:\MASTER_AI_WORKSTATION\MASTER_AI_WORKSTATION\MASTER_CORE_V1"):
        self.workspace = workspace
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
        banner = f"""
\033[38;5;51m╔══════════════════════════════════════════════════════════════════════════════╗
║ \033[1m\033[38;5;226m🤖 MASTER AUTONOMOUS ReAct AGENT \033[0m\033[38;5;51m— \033[38;5;198mMULTI-CORE AI BRAIN v22.0\033[38;5;51m             ║
║ \033[38;5;248m📂 WORKSPACE\033[38;5;51m :\033[38;5;253m {self.workspace:<60}\033[38;5;51m ║
║ \033[38;5;248m⚙️ STATUS   \033[38;5;51m :\033[38;5;46m ONLINE \033[38;5;240m|\033[38;5;226m 🧠 4-CORE AI BRAIN \033[38;5;51m:\033[38;5;46m ACTIVE \033[38;5;240m|\033[38;5;45m 💾 DB \033[38;5;51m:\033[38;5;46m READY\033[38;5;51m   ║
║ \033[38;5;248m🗣️ LANGUAGE \033[38;5;51m :\033[38;5;213m [{self.current_language.upper():<60}]\033[38;5;51m ║
╚══════════════════════════════════════════════════════════════════════════════╝\033[0m
"""
        print(banner)

    def print_agent_box(self, title, message, color_code="\033[38;5;51m", text_color="\033[38;5;253m"):
        print(f"{color_code}╭─[ \033[1m{title} \033[0m{color_code}] ─────────────────────────────────────────────────────────────\033[0m")
        for paragraph in message.split("\n"):
            clean_p = paragraph.replace("**", "").replace("### ", "🔹 ").replace("## ", "⚡ ")
            if not clean_p.strip():
                print(f"{color_code}│\033[0m")
                continue
            wrapped_lines = textwrap.wrap(clean_p, width=72)
            for line in wrapped_lines:
                print(f"{color_code}│{text_color} {line}\033[0m")
        print(f"{color_code}╰──────────────────────────────────────────────────────────────────────────────\033[0m\n")

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
        cmd_lower = command.lower()
        if "scan" in cmd_lower or "list" in cmd_lower or "show files" in cmd_lower:
            files = os.listdir(self.workspace)
            msg = "Workspace Files Found:\n" + "\n".join([f" 📄 {f}" for f in files[:15]])
            self.print_agent_box("📁 FILE SYSTEM", msg, "\033[38;5;226m")
        elif "read" in cmd_lower:
            words = command.split()
            filename = next((w for w in words if "." in w), None)
            if filename and os.path.exists(os.path.join(self.workspace, filename)):
                with open(os.path.join(self.workspace, filename), "r", encoding="utf-8") as f:
                    self.print_agent_box(f"👁️ READING: {filename}", f.read()[:800], "\033[38;5;46m")
            else:
                self.print_agent_box("❌ ERROR", "Specify a valid filename in your workspace (e.g., read evolution_history.log).", "\033[38;5;196m")
        elif any(w in cmd_lower for w in ["create", "write", "make file"]):
            filename = "autonomous_script.py" if "python" in cmd_lower else "agent_notes.txt"
            filepath = os.path.join(self.workspace, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# Generated by Master Autonomous Agent\n# Command: {command}\nprint('Autonomous file execution successful!')\n")
            self.print_agent_box("📝 FILE CREATED", f"Saved new file to: {filepath}", "\033[38;5;46m")

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
        lang_instruction = {
            "english": "Reply in clear, helpful English with numbered steps.",
            "bengali": "Reply in natural Bengali (বাংলা script) with clear numbered steps.",
            "hinglish": "Reply in conversational Hinglish/Benglish (English alphabet) with clear numbered steps."
        }.get(self.current_language, "Reply in clear English.")

        system_prompt = (
            "You are Rohan's Master Autonomous AI Studio Agent. "
            "Provide a direct, practical, step-by-step answer to the user's question. "
            "Do not use markdown tables. "
            f"{lang_instruction}"
        )

        user_content = user_prompt
        if web_context:
            user_content = f"User Question: {user_prompt}\n\nLive Web Context (use if helpful):\n{web_context}"

        # CORE 1: Pollinations OpenAI-Compatible Endpoint with Browser Headers
        try:
            payload = {
                "model": "openai",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
            }
            headers = dict(BROWSER_HEADERS)
            headers["Content-Type"] = "application/json"
            resp = requests.post(
                "https://text.pollinations.ai/openai",
                json=payload,
                headers=headers,
                timeout=20
            )
            if resp.status_code == 200:
                data = resp.json()
                ans = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if len(ans) > 25:
                    return ans
        except Exception:
            pass

        # CORE 2: Pollinations Direct Text Endpoint with Browser Headers
        try:
            short_prompt = f"Give a clear step-by-step guide for: {user_prompt}. {lang_instruction}"
            url = f"https://text.pollinations.ai/{urllib.parse.quote(short_prompt)}?model=openai"
            resp = requests.get(url, headers=BROWSER_HEADERS, timeout=20)
            if resp.status_code == 200 and len(resp.text.strip()) > 25 and "<html" not in resp.text.lower():
                return resp.text.strip()
        except Exception:
            pass

        # CORE 3: DuckDuckGo Native AI Chat (if supported by installed ddgs version)
        if DDGS_AVAILABLE:
            try:
                with DDGS() as ddgs:
                    if hasattr(ddgs, "chat"):
                        ans = ddgs.chat(f"{user_prompt}. {lang_instruction}")
                        if ans and len(ans.strip()) > 25:
                            return ans.strip()
            except Exception:
                pass

        raise RuntimeError("All cloud LLM cores unreachable")

    def superpower_brain_search(self, user_prompt):
        print(f"\033[38;5;226m╭─[ 🧠 MULTI-CORE AI BRAIN ACTIVATED ] ─────────────────────────────────────\033[0m")

        clean = user_prompt.strip()
        for prefix in ["open google and search", "open chat gpt and type", "give me result in here", "search for"]:
            clean = re.sub(prefix, "", clean, flags=re.IGNORECASE).strip()
        if not clean:
            clean = user_prompt

        print(f"\033[38;5;226m│\033[0m \033[38;5;45m🌐 Step 1/2: Searching live internet sources for '{clean}'...\033[0m")
        web_context, urls = self.fetch_live_web_context(clean)
        if web_context:
            print(f"\033[38;5;226m│\033[0m \033[38;5;46m✔ Live web sources captured!\033[0m")
        else:
            print(f"\033[38;5;226m│\033[0m \033[38;5;208mℹ️ Using direct AI reasoning engine...\033[0m")

        print(f"\033[38;5;226m│\033[0m \033[38;5;213m⚡ Step 2/2: Generating step-by-step AI response...\033[0m")
        try:
            final_answer = self.ask_ai_llm_brain(clean, web_context)
            print(f"\033[38;5;226m│\033[0m \033[38;5;46m✅ AI Brain synthesis complete! Saving to database.\033[0m")
        except Exception:
            print(f"\033[38;5;226m│\033[0m \033[38;5;208m🔄 Cloud AI busy; engaging Core 4 (Deep Webpage Article Reader)...\033[0m")
            deep_article = self.deep_read_webpage(urls)
            if deep_article:
                final_answer = deep_article
            elif web_context:
                final_answer = f"Top Web Findings:\n{web_context}"
            else:
                final_answer = "Could not reach online sources. Please check your internet connection."

        print(f"\033[38;5;226m╰──────────────────────────────────────────────────────────────────────────────\033[0m\n")

        self.save_to_memory(clean, final_answer)
        footer = f"\n\n(💾 Saved to knowledge_base.json | Total learned topics: {len(self.memory_db)})"
        self.print_agent_box("🤖 SUPER INTELLIGENT ANSWER", final_answer + footer, "\033[38;5;46m", "\033[38;5;253m")

    def chat_response(self, user_prompt):
        prompt_lower = user_prompt.lower().strip()
        print(f"\033[38;5;208m╭─[ \033[1m👤 ROHAN \033[0m\033[38;5;208m] ─────────────────────────────────────────────────────────────\033[0m")
        print(f"\033[38;5;208m│\033[0m \033[38;5;253m{user_prompt}\033[0m")
        print(f"\033[38;5;208m╰──────────────────────────────────────────────────────────────────────────────\033[0m")

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
            self.execute_os_task(user_prompt)

        elif any(w in prompt_lower for w in ["what did you learn", "check memory", "show memory"]):
            mem_count = len(self.memory_db)
            recent_keys = list(self.memory_db.keys())[-5:]
            topics_str = "\n".join([f" • {k}" for k in recent_keys]) if recent_keys else " • No topics saved yet."
            msg = f"Total Learned Topics in Database: {mem_count}\n\nRecent Topics:\n{topics_str}\n\nLatest Log:\n{self.active_intel}"
            self.print_agent_box("🧠 AGENT MEMORY DATABASE", msg, "\033[38;5;198m")

        else:
            self.superpower_brain_search(user_prompt)

cli_style = Style([
    ('qmark', 'fg:#00ffff bold'),
    ('question', 'fg:#ffffff bold'),
    ('answer', 'fg:#00ff00 bold'),
    ('pointer', 'fg:#ff00ff bold'),
    ('selected', 'fg:#00ff00 bold'),
])

if __name__ == "__main__":
    agent = MasterSystemAgent()
    agent.print_banner()

    while True:
        try:
            print(f"\033[38;5;46m╭─[\033[38;5;253mROHAN\033[38;5;46m] \033[38;5;226m⚡ \033[38;5;51m[MASTER_CORE] \033[38;5;248m─[\033[38;5;213m{agent.current_language.upper()}\033[38;5;248m]\033[0m")
            action = questionary.select(
                "Choose an action:",
                choices=[
                    "💬 Chat / Ask Anything (AI Brain + Live Web)",
                    "⚙️ OS & File Tasks (Read/Write/Scan)",
                    "🧠 Check Learned Memory Database",
                    "🗣️ Switch Language",
                    "❌ Exit"
                ],
                style=cli_style,
                pointer="➤"
            ).ask()

            if not action or action == "❌ Exit":
                agent.print_agent_box("🛑 SYSTEM HALT", "System gracefully shut down. Goodbye, Rohan!", "\033[38;5;196m")
                break

            if action.startswith("💬"):
                user_input = input("\033[38;5;46m╰─➤ Enter Prompt: \033[0m").strip()
                if user_input:
                    print("")
                    agent.chat_response(user_input)

            elif action.startswith("⚙️"):
                task = input("\033[38;5;46m╰─➤ Describe File Task (scan files / read <file> / create a file): \033[0m").strip()
                if task:
                    print("")
                    agent.execute_os_task(task)

            elif action.startswith("🧠"):
                print("")
                agent.chat_response("check memory")

            elif action.startswith("🗣️"):
                lang = questionary.select(
                    "Select your preferred language:",
                    choices=["English", "Bengali (বাংলা)", "Hinglish (Benglish)"],
                    style=cli_style,
                    pointer="➤"
                ).ask()
                if lang:
                    agent.set_language(lang)

        except KeyboardInterrupt:
            print("\n")
            agent.print_agent_box("🛑 SYSTEM HALT", "Agent safely stopped.", "\033[38;5;196m")
            break