#!/usr/bin/env python3
"""Voice front-end for the shared offline-first MasterSystemAgent brain."""
import os, sys, subprocess
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from master_studio_agent import MasterSystemAgent

def main():
    agent = MasterSystemAgent(workspace=ROOT)
    print("\n🎙️ MASTER AGENT VOICE MODE — shared memory/core")
    print("Speak using Android Termux speech-to-text. Press Ctrl+C to exit.")
    while True:
        try:
            print("\n[🎤] Listening...")
            result = subprocess.run(["termux-speech-to-text"], capture_output=True, text=True, timeout=90)
            prompt = (result.stdout or "").strip()
            if not prompt:
                print("No speech recognized. Try again.")
                continue
            print("[You]", prompt)
            if prompt.lower() in {"exit", "quit", "বন্ধ", "বাহির"}:
                break
            agent.chat_response(prompt)
            # Android's installed TTS engine; no gTTS/cloud audio generation.
            try:
                subprocess.Popen(["termux-tts-speak", "আপনার অনুরোধ গ্রহণ করা হয়েছে। বিস্তারিত উত্তর টার্মিনালে দেখুন।"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        except FileNotFoundError:
            print("Missing Termux:API command. Install Termux:API app and package, then retry.")
            break
        except KeyboardInterrupt:
            break
        except Exception as exc:
            print("Voice input error:", exc)

if __name__ == "__main__":
    main()
