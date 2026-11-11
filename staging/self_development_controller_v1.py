import json
import ast
import re
import os
import sys
import time
import threading
from pathlib import Path

os.system("")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

class UI:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @staticmethod
    def box(title: str, content: str, color: str = "\033[96m", numbered: bool = False):
        width = 75
        clean_title = f" {title} "
        top_bar = "─" * max(1, (width - len(clean_title) - 3))
        print(f"\n{color}╭─{UI.BOLD}{clean_title}{UI.RESET}{color}{top_bar}╮{UI.RESET}", flush=True)
        lines = content.strip().splitlines() if content.strip() else ["(empty)"]
        for idx, line in enumerate(lines, 1):
            if numbered:
                print(f"{color}│{UI.RESET} {UI.GRAY}{idx:2d} │{UI.RESET} {line}", flush=True)
            else:
                print(f"{color}│{UI.RESET} {line}", flush=True)
        print(f"{color}╰{'─' * (width - 2)}╯{UI.RESET}", flush=True)

    @staticmethod
    def step(badge: str, message: str, color: str = "\033[96m"):
        print(f"{color}{UI.BOLD}{badge}{UI.RESET} {message}", flush=True)

class SelfDevelopmentController:
    def __init__(self, callbacks: dict, project_root: str):
        self.callbacks = callbacks
        self.project_root = Path(project_root)
        self.operation_count = 0
        self.max_operations = 30
        self.max_iterations = 4

    @classmethod
    def from_agent_namespace(cls, namespace: dict, project_root: str):
        required_callbacks = ["tool_tree", "tool_read", "tool_write", "ollama", "tool_search"]
        callbacks = {req: namespace.get(req) for req in required_callbacks}
        return cls(callbacks, project_root)

    def _track_operation(self, op_name: str):
        self.operation_count += 1
        if self.operation_count > self.max_operations:
            raise RuntimeError("ABORT: Max operations exceeded.")

    def _extract_ollama_text(self, raw_response) -> str:
        if isinstance(raw_response, dict):
            if "message" in raw_response and isinstance(raw_response["message"], dict):
                return str(raw_response["message"].get("content", ""))
            return str(raw_response.get("content", raw_response.get("response", json.dumps(raw_response))))
        return str(raw_response)

    def _call_ollama_pro(self, messages: list, spinner_label: str, done_label: str) -> str:
        self._track_operation(spinner_label)
        stop_event = threading.Event()
        start_time = time.time()
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        def animate():
            idx = 0
            while not stop_event.wait(0.12):
                elapsed = time.time() - start_time
                sys.stdout.write(f"\r{UI.MAGENTA}{UI.BOLD}{frames[idx % len(frames)]}{UI.RESET} {UI.CYAN}{spinner_label}{UI.RESET} {UI.GRAY}({elapsed:.1f}s){UI.RESET}   ")
                sys.stdout.flush()
                idx += 1

        t = threading.Thread(target=animate, daemon=True)
        t.start()
        try:
            raw_res = self.callbacks["ollama"](messages)
        finally:
            stop_event.set()
            t.join(timeout=0.5)

        total_time = time.time() - start_time
        sys.stdout.write(f"\r{UI.GREEN}{UI.BOLD}✔{UI.RESET} {UI.BOLD}{done_label}{UI.RESET} {UI.GRAY}({total_time:.1f}s){UI.RESET}{' ' * 20}\n")
        sys.stdout.flush()
        return self._extract_ollama_text(raw_res).strip()

    def search_internet(self, query: str) -> str:
        self._track_operation("tool_search")
        UI.step("🌐", f"Browsing the web for: '{query}'...", UI.BLUE)
        return self.callbacks["tool_search"](query)

    def autonomous_research(self, objective: str) -> str:
        prompt = f"Extract 2-3 broad search keywords for this task: '{objective}'. DO NOT use quotes. Reply with ONLY the keywords."
        query = self._call_ollama_pro([{"role": "user", "content": prompt}], "Formulating Smart Query...", "Query Formulated")
        search_results = self.search_internet(query)
        UI.box(f"🌐 Web Research Results ({query})", search_results, UI.GRAY)
        return search_results

    def plan_task(self, objective: str, web_context: str) -> str:
        prompt = f"Context from Web:\n{web_context}\n\nTask: {objective}\nPlan a Python script based on this context. 3 bullet points."
        return self._call_ollama_pro([{"role": "user", "content": prompt}], "✨ Planning Architecture...", "✨ Plan Ready")

    def generate_code_changes(self, objective: str, plan: str, error_feedback: str = "") -> dict:
        repair_note = f"\n⚠️ PREVIOUS CODE FAILED:\n{error_feedback}\nFIX THE ERROR AND REWRITE. Ensure all quotes are closed." if error_feedback else ""
        prompt = (
            f"Objective: {objective}\nPlan: {plan}\n{repair_note}\n\n"
            f"Return ONLY valid JSON format with keys \"file_path\" and \"code\".\n"
            f"Example:\n{{\"file_path\": \"MASTER_CORE_V1/staging/anim.py\", \"code\": \"print('hi')\"}}"
        )
        label = "🔧 Self-Healing & Debugging Code..." if error_feedback else "💻 Writing Code..."
        done_lbl = "🔧 Bug Fixed & Code Generated" if error_feedback else "💻 Code Generated"
        response = self._call_ollama_pro([{"role": "user", "content": prompt}], label, done_lbl)

        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        candidate = match.group(0) if match else cleaned

        try: 
            parsed = json.loads(candidate)
            if "file_path" in parsed: return parsed
        except: pass
        
        path_match = re.search(r'["\']file_path["\']\s*:\s*["\']([^"\']+)["\']', response)
        code_block = re.search(r"```(?:python)?\s*(.*?)```", response, re.DOTALL)
        if code_block and path_match:
            return {"file_path": path_match.group(1), "code": code_block.group(1).strip()}
        return {"error": "Invalid output format.", "raw": response}

    def execute_development_task(self, objective: str) -> dict:
        print(f"\n{UI.GRAY}{'━' * 75}{UI.RESET}", flush=True)
        UI.step("🎯", f"{UI.BOLD}Mission:{UI.RESET} {objective}", UI.CYAN)
        
        web_context = ""
        if "search" in objective.lower() or "research" in objective.lower() or "internet" in objective.lower():
            web_context = self.autonomous_research(objective)
            
        plan = self.plan_task(objective, web_context)
        error_feedback = ""
        
        for attempt in range(1, self.max_iterations + 1):
            gen_data = self.generate_code_changes(objective, plan, error_feedback)
            if "error" in gen_data:
                error_feedback = gen_data["error"]
                if attempt == self.max_iterations: return {"status": "error", "message": error_feedback}
                UI.step("🔄", f"Format error. Deep Healing (Attempt {attempt+1})...", UI.YELLOW)
                continue

            target_path = gen_data.get("file_path", "").replace("\\", "/")
            code_content = gen_data.get("code", "").strip()
            
            # EMPTY CODE CATCHER (The new fix!)
            if not code_content:
                error_feedback = "You returned an empty string for the code! You MUST write the actual Python code inside the 'code' JSON key."
                UI.step("✖", f"AI returned a blank file! Triggering AI Auto-Fix (Attempt {attempt+1})...", UI.RED)
                continue

            UI.box(f"📄 Proposed Module: {target_path} (Attempt {attempt})", code_content, UI.CYAN, numbered=True)

            try:
                ast.parse(code_content)
                UI.step("✔", "Syntax Verification: PASSED", UI.GREEN)
                break
            except SyntaxError as e:
                error_feedback = f"SyntaxError: {str(e)}"
                UI.step("✖", f"Syntax Error Found: {e}. Triggering AI Auto-Fix...", UI.RED)
                if attempt == self.max_iterations: return {"status": "error", "message": error_feedback}

        UI.step("🛡️", "Submitting to Workstation Safety Adapter...", UI.YELLOW)
        result = self.callbacks["tool_write"]({"path": target_path, "content": code_content}, self.project_root)
        
        if isinstance(result, dict) and result.get("status") == "pending_approval":
            UI.box("🛡️ SAFETY GATE: APPROVAL REQUIRED", f"Ticket ID: {result.get('ticket_id')}\nPath: {result.get('path')}\nReview: http://127.0.0.1:8765/safety", UI.YELLOW)
        return result