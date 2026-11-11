import os
import sys

# Dynamically sets workspace to current folder on Android Termux or Cloud when Office PC is OFF
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from master_studio_agent import MasterSystemAgent, cli_style
import questionary

if __name__ == "__main__":
    agent = MasterSystemAgent(workspace=CURRENT_DIR)
    agent.print_banner()
    print(f"\033[38;5;46m[PORTABLE MODE ACTIVE] Running independently of Office PC in: {CURRENT_DIR}\033[0m\n")

    while True:
        try:
            action = questionary.select(
                "Choose an action (Portable Mode):",
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
                break
            if action.startswith("💬"):
                user_input = input("╰─➤ Enter Prompt: ").strip()
                if user_input:
                    agent.chat_response(user_input)
            elif action.startswith("⚙️"):
                task = input("╰─➤ Describe File Task: ").strip()
                if task:
                    agent.execute_os_task(task)
            elif action.startswith("🧠"):
                agent.chat_response("check memory")
            elif action.startswith("🗣️"):
                lang = questionary.select("Select language:", choices=["English", "Bengali (বাংলা)", "Hinglish (Benglish)"], style=cli_style).ask()
                if lang:
                    agent.set_language(lang)
        except KeyboardInterrupt:
            break