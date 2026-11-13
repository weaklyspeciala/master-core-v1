with open("pc_off_portable_runner.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

out = []
for line in lines:
    if "Could not reach online sources" in line:
        ind = " " * (len(line) - len(line.lstrip()))
        out.append(ind + "try:\n")
        out.append(ind + "    import requests, bs4\n")
        out.append(ind + "    print('\\n[ 🌐 SUPERPOWER ACTIVATED ] Searching live internet...')\n")
        out.append(ind + "    r = requests.post('https://lite.duckduckgo.com/lite/', data={'q': user_prompt}, timeout=10)\n")
        out.append(ind + "    s = bs4.BeautifulSoup(r.text, 'html.parser')\n")
        out.append(ind + "    d = [t.text.strip() for t in s.find_all('td', class_='result-snippet')]\n")
        out.append(ind + "    print('\\n---\\n'.join(d[:3]) if d else '⚠️ Could not find direct data.')\n")
        out.append(ind + "except Exception as e:\n")
        out.append(ind + "    print('❌ Superpower Network Error:', e)\n")
    else:
        out.append(line)

with open("pc_off_portable_runner.py", "w", encoding="utf-8") as f:
    f.writelines(out)
print("[SUCCESS] Power injected safely!")
