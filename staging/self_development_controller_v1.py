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
        prompt = f"Context from Web:\n{web_context}\n\nTask: {objective}\nCreate a concise task plan in 3 bullet points. Do not generate code."
        return self._call_ollama_pro([{"role": "user", "content": prompt}], "✨ Planning Architecture...", "✨ Plan Ready")

    def generate_code_changes(self, objective: str, plan: str, error_feedback: str = "") -> dict:
        repair_note = f"\nPREVIOUS CODE FAILED.\n{error_feedback}\nReturn the COMPLETE corrected Python source in the JSON code value. Do not repeat the previous error." if error_feedback else ""
        prompt = (
            f"Objective: {objective}\nPlan: {plan}\n{repair_note}\n\n"
            f"IMPORTANT: The value of \"code\" MUST be complete, syntactically valid Python source code. "
            f"If the objective asks for a comment, begin the Python comment with #. "
            f"Never put plain un-commented natural language in the code value.\n"
            f"Return ONLY valid JSON with exactly the keys \"file_path\" and \"code\".\n"
            f"Example: {{\"file_path\": \"staging/example.py\", \"code\": \"# Example comment\\nprint('hi')\"}}"
        )

        label = "🔧 Self-Healing & Debugging Code..." if error_feedback else "💻 Writing Code..."
        done_lbl = "🔧 Bug Fixed & Code Generated" if error_feedback else "💻 Code Generated"
        response = self._call_ollama_pro(
            [{"role": "user", "content": prompt}], label, done_lbl
        )

        if not isinstance(response, str):
            return {"error": "Invalid output format.", "raw": response}

        cleaned = response.strip()
        decoder = json.JSONDecoder()
        valid_payloads = []

        for index, character in enumerate(cleaned):
            if character != "{":
                continue

            try:
                parsed, _ = decoder.raw_decode(cleaned[index:])
            except (json.JSONDecodeError, ValueError):
                continue

            if not isinstance(parsed, dict):
                continue

            if set(parsed.keys()) != {"file_path", "code"}:
                continue

            file_path = parsed.get("file_path")
            code = parsed.get("code")

            if (
                isinstance(file_path, str)
                and file_path.strip()
                and isinstance(code, str)
                and code.strip()
            ):
                valid_payloads.append({
                    "file_path": file_path.strip(),
                    "code": code
                })

        if len(valid_payloads) == 1:
            return valid_payloads[0]

        if len(valid_payloads) == 0:
            import re

            path_matches = re.findall(
                r'["\']file_path["\']\s*:\s*["\']([^"\']+)["\']',
                response
            )

            code_blocks = re.findall(
                r'```(?:python)?[ \t]*\r?\n(.*?)```',
                response,
                flags=re.IGNORECASE | re.DOTALL
            )

            if len(path_matches) == 1 and len(code_blocks) == 1:
                file_path = path_matches[0].strip()
                code = code_blocks[0]

                if file_path and code.strip():
                    return {"file_path": file_path, "code": code}

        return {"error": "Invalid output format.", "raw": response}

    def _run_quality_gate(self) -> bool:
        """Run the existing static Quality Gate before approval submission."""
        import subprocess

        root = self.project_root.resolve()
        gate_path = root / "staging" / "autonomous_quality_gate.py"

        if not gate_path.is_file():
            UI.step("✖", "Quality Gate missing. Approval blocked.", UI.RED)
            return False

        if gate_path.resolve().parents[1] != root:
            UI.step("✖", "Quality Gate root mismatch. Approval blocked.", UI.RED)
            return False

        UI.step("🧪", "Running Autonomous Quality Gate...", UI.CYAN)

        try:
            result = subprocess.run(
                [sys.executable, str(gate_path)],
                cwd=str(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            UI.step("✖", f"Quality Gate execution failed: {exc}", UI.RED)
            return False

        output = (result.stdout or "") + (result.stderr or "")
        if output.strip():
            print(output.rstrip(), flush=True)

        if result.returncode != 0:
            UI.step("⛔", "QUALITY GATE FAILED. Approval blocked.", UI.RED)
            return False

        UI.step("✔", "QUALITY GATE PASSED.", UI.GREEN)
        return True

    def execute_development_task(self, objective: str) -> dict:
        """Execute a bounded development task; planning requests never generate code."""
        self.operation_count = 0

        print(f"\\n{UI.GRAY}{'━' * 75}{UI.RESET}", flush=True)
        UI.step("🎯", f"{UI.BOLD}Mission:{UI.RESET} {objective}", UI.CYAN)

        value = objective.strip().lower()

        execution_markers = (
            "develop:", "self-upgrade:", "upgrade:",
            "implement the plan", "implement:", "write code",
            "create the file", "modify files", "make changes",
            "apply changes", "fix the code",
            "ইমপ্লিমেন্ট কর", "কোড লিখ", "ফাইল তৈরি কর",
            "পরিবর্তন কর", "ঠিক কর"
        )

        plan_markers = (
            "plan", "roadmap", "পরিকল্পনা", "কর্মপরিকল্পনা"
        )

        request_markers = (
            "prepare", "create", "give", "show", "report",
            "analyze", "প্রস্তুত", "তৈরি", "দাও", "দেখাও"
        )

        explicit_execution = any(
            marker in value for marker in execution_markers
        )

        planning_only = (
            not explicit_execution
            and any(marker in value for marker in plan_markers)
            and any(marker in value for marker in request_markers)
        )

        web_context = ""
        if any(word in value for word in ("search", "research", "internet")):
            web_context = self.autonomous_research(objective)

        plan = self.plan_task(objective, web_context)

        if planning_only:
            UI.box("📋 DEVELOPMENT PLAN", plan, UI.BLUE)
            UI.step(
                "✔",
                "Planning complete. No code generated and no approval ticket created.",
                UI.GREEN
            )
            return {
                "status": "planned",
                "plan": plan,
                "message": "Planning-only request completed; project files unchanged."
            }

        feedback = ""
        retry_limit = min(max(1, self.max_iterations), 2)

        for attempt in range(1, retry_limit + 1):
            data = self.generate_code_changes(objective, plan, feedback)

            if not isinstance(data, dict) or "error" in data:
                feedback = (
                    str(data.get("error", "Invalid generator response."))
                    if isinstance(data, dict)
                    else "Generator returned an invalid response."
                )
                if attempt == retry_limit:
                    return {"status": "error", "message": feedback}
                continue

            path = str(data.get("file_path", "")).replace("\\", "/").strip()
            code = str(data.get("code", "")).strip()

            if not path or not code:
                feedback = "Return non-empty file_path and complete code."
                if attempt == retry_limit:
                    return {"status": "error", "message": feedback}
                continue

            try:
                ast.parse(code)
            except SyntaxError as exc:
                feedback = (
                    f"SyntaxError: {exc}. "
                    "Return the complete corrected source."
                )
                if attempt == retry_limit:
                    return {"status": "error", "message": feedback}
                continue

            if not self._run_quality_gate():
                return {
                    "status": "blocked",
                    "message": "Pre-change Quality Gate failed; no file changed."
                }

            result = self.callbacks["tool_write"](
                {"path": path, "content": code},
                self.project_root
            )

            if isinstance(result, dict) and result.get("status") == "rolled_back":
                feedback = (
                    "The previous change failed post-change checks and was "
                    "rolled back. Fix the cause. Test details: "
                    + str(result.get("post_change_checks", ""))
                )
                if attempt < retry_limit:
                    UI.step(
                        "🔄",
                        f"Verified rollback. Final repair attempt {attempt + 1}/{retry_limit}.",
                        UI.YELLOW
                    )
                    continue

            return result

        return {
            "status": "error",
            "message": "Bounded development retry limit reached."
        }

