#!/usr/bin/env python3
"""Top-level launcher for the unified text/voice Master Agent."""
import os, sys, subprocess
ROOT = os.path.dirname(os.path.abspath(__file__))
if __name__ == "__main__":
    print("MASTER AUTONOMOUS AGENT — Unified Launcher")
    print("1. Text Agent")
    print("2. Voice Agent")
    print("3. Exit")
    choice = input("Select: ").strip()
    if choice == "1":
        raise SystemExit(subprocess.call([sys.executable, os.path.join(ROOT, "core_backend.py")], cwd=ROOT))
    elif choice == "2":
        raise SystemExit(subprocess.call([sys.executable, os.path.join(ROOT, "voice_plugin.py")], cwd=ROOT))
    else:
        print("Exiting.")
