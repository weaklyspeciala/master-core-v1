import os

with open("pc_off_portable_runner.py", "r", encoding="utf-8") as f:
    content = f.read()

BRAIN = """
import os, subprocess, requests, bs4

def level2_autonomous_brain(command):
    print(f"\\n[ 🧠 LEVEL 2 SYSTEM ] {command}")
    cmd = command.lower()
    try:
        if "update" in cmd or "আপডেট" in cmd:
            return subprocess.getoutput("git pull origin main")
        elif cmd.startswith("run:"):
            return subprocess.getoutput(command[4:].strip())
        elif cmd.startswith("make file:"):
            p = command.replace("make file:", "").split("|")
            with open(p[0].strip(), "w", encoding="utf-8") as f:
                f.write(p[1].strip() if len(p)>1 else "")
            return "✅ File saved successfully."
        else:
            r = requests.post('https://lite.duckduckgo.com/lite/', data={'q': command}, timeout=10)
            s = bs4.BeautifulSoup(r.text, 'html.parser')
            d = [t.text.strip() for t in s.find_all('td', class_='result-snippet')]
            return '\\n---\\n'.join(d[:3]) if d else '⚠️ No data found.'
    except Exception as e:
        return str(e)
"""

if "level2_autonomous_brain" not in content:
    content = BRAIN + "\n" + content.replace("Could not reach online sources. Please check your internet connection.", "print(level2_autonomous_brain(user_prompt))")
    with open("pc_off_portable_runner.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("[SUCCESS] LEVEL 2 System Active!")
