import os
try:
    with open("pc_off_portable_runner.py", "r", encoding="utf-8") as f:
        c = f.read()
        
    BRAIN = """
import os, subprocess, requests, bs4

def level2_autonomous_brain(command):
    print(f"\\n[ 🧠 LEVEL 2 SYSTEM ] Analyzing Command: {command}")
    cmd_lower = command.lower()
    
    try:
        # ১. নিজেকে নিজে আপডেট করার ক্ষমতা
        if "আপডেট" in cmd_lower or "update" in cmd_lower:
            print("[ 🔄 ] Updating agent code from GitHub...")
            return subprocess.getoutput("git pull origin main")
            
        # ২. টার্মিনাল কমান্ড রান করার ক্ষমতা (Trigger: run: )
        elif cmd_lower.startswith("run:"):
            return subprocess.getoutput(command[4:].strip())
            
        # ৩. ফাইল তৈরি বা ওভাররাইট করার ক্ষমতা (Trigger: make file: name | content)
        elif cmd_lower.startswith("make file:"):
            parts = command.replace("make file:", "").split("|")
            fname = parts[0].strip()
            fcontent = parts[1].strip() if len(parts) > 1 else ""
            with open(fname, "w", encoding="utf-8") as file:
                file.write(fcontent)
            return f"✅ File '{fname}' created/overwritten successfully."
            
        # ৪. লাইভ ইন্টারনেট ডেটা স্ক্র্যাপিং
        else:
            print('[ 🌐 ] Fetching live data...')
            r = requests.post('https://lite.duckduckgo.com/lite/', data={'q': command}, timeout=10)
            s = bs4.BeautifulSoup(r.text, 'html.parser')
            d = [t.text.strip() for t in s.find_all('td', class_='result-snippet')]
            return '\\n---\\n'.join(d[:3]) if d else '⚠️ No exact data found on live web.'
            
    except Exception as e:
        return f"❌ Level 2 System Error: {e}"
"""

    if "level2_autonomous_brain" not in c:
        c = BRAIN + "\n" + c.replace("Could not reach online sources. Please check your internet connection.", "print(level2_autonomous_brain(user_prompt))")
        with open("pc_off_portable_runner.py", "w", encoding="utf-8") as f:
            f.write(c)
        print("[SUCCESS] Agent is now upgraded to LEVEL 2!")
except Exception as e:
    print("Error:", e)
