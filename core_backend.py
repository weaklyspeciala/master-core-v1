#!/usr/bin/env python3
"""MASTER CORE portable entry point. Uses the single MasterSystemAgent brain."""
import os, sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
from master_studio_agent import MasterSystemAgent, cli_style
import questionary

def main():
    agent = MasterSystemAgent(workspace=CURRENT_DIR)
    agent.print_banner()
    print("[PORTABLE MODE] Workspace:", CURRENT_DIR)
    while True:
        try:
            action = questionary.select(
                "Choose an action:",
                choices=[
                    "💬 Chat / Ask Anything (Offline-First AI Core)",
                    "⚙️ OS & File Tasks (Read/Write/Scan)",
                    "🧠 Check Learned Memory Database",
                    "🗣️ Switch Language",
                    "❌ Exit",
                ], style=cli_style, pointer="➤"
            ).ask()
            if not action or action.startswith("❌"):
                break
            if action.startswith("💬"):
                prompt = input("╰─➤ Enter Prompt: ").strip()
                if prompt:
                    agent.chat_response(prompt)
            elif action.startswith("⚙️"):
                task = input("╰─➤ Describe File Task: ").strip()
                if task:
                    agent.execute_os_task(task)
            elif action.startswith("🧠"):
                agent.chat_response("check memory")
            elif action.startswith("🗣️"):
                lang = questionary.select(
                    "Select language:",
                    choices=["English", "Bengali (বাংলা)", "Hinglish (Benglish)"],
                    style=cli_style
                ).ask()
                if lang:
                    agent.set_language(lang)
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
