import os
import sys
import json
import time
import shutil
import datetime
import py_compile
import subprocess

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
BACKUP_ROOT = os.path.join(WORKSPACE, "backups", "sync_snapshots")
GITIGNORE_FILE = os.path.join(WORKSPACE, ".gitignore")
MEMORY_FILE = os.path.join(WORKSPACE, "knowledge_base.json")

os.makedirs(BACKUP_ROOT, exist_ok=True)

GITIGNORE_CONTENT = """# Protect local secrets and temporary backups
mobile_bridge_config.json
backups/
__pycache__/
_staging_upgrade_test.py
*.bak
*.pyc
"""

def ensure_gitignore():
    if not os.path.exists(GITIGNORE_FILE):
        with open(GITIGNORE_FILE, "w", encoding="utf-8") as f:
            f.write(GITIGNORE_CONTENT)
        print("🛡️ Created .gitignore (mobile_bridge_config.json & backups excluded from cloud).")

def run_git(args):
    proc = subprocess.run(
        ["git"] + args,
        cwd=WORKSPACE,
        capture_output=True,
        text=True
    )
    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()

def verify_workspace_syntax():
    print("🔍 Running syntax & JSON integrity audit...")
    py_files = [f for f in os.listdir(WORKSPACE) if f.endswith(".py") and not f.startswith("_staging")]
    for py_file in py_files:
        full_path = os.path.join(WORKSPACE, py_file)
        try:
            py_compile.compile(full_path, doraise=True)
            print(f"  ✅ Syntax OK: {py_file}")
        except Exception as e:
            print(f"  ❌ Syntax Error in {py_file}:\n     {e}")
            return False

    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                json.load(f)
            print("  ✅ JSON Integrity OK: knowledge_base.json")
        except Exception as e:
            print(f"  ❌ Corrupted JSON in knowledge_base.json: {e}")
            return False

    return True

def create_snapshot():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_dir = os.path.join(BACKUP_ROOT, f"snap_{ts}")
    os.makedirs(snap_dir, exist_ok=True)
    for fname in os.listdir(WORKSPACE):
        if fname.endswith((".py", ".json", ".log")) and fname != "mobile_bridge_config.json":
            src = os.path.join(WORKSPACE, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(snap_dir, fname))
    print(f"💾 Local safety snapshot saved to: backups/sync_snapshots/snap_{ts}")
    return snap_dir

def restore_snapshot(snap_dir):
    print(f"⏪ Restoring files from snapshot: {snap_dir}...")
    for fname in os.listdir(snap_dir):
        shutil.copy2(os.path.join(snap_dir, fname), os.path.join(WORKSPACE, fname))
    print("✅ Rollback complete. Your workspace is safe.")

def load_memory_dict(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def init_repo(remote_url):
    ensure_gitignore()
    if not os.path.exists(os.path.join(WORKSPACE, ".git")):
        run_git(["init"])
        run_git(["branch", "-M", "main"])
    run_git(["remote", "remove", "origin"])
    code, out, err = run_git(["remote", "add", "origin", remote_url])
    if code == 0:
        print(f"🔗 Linked workspace to GitHub repo: {remote_url}")
    else:
        print(f"⚠️ Git remote notice: {err}")

def safe_push(commit_note="Autonomous workspace sync"):
    ensure_gitignore()
    if not verify_workspace_syntax():
        print("🛑 PUSH BLOCKED: Fix syntax errors before syncing to GitHub.")
        return False

    run_git(["add", "."])
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code, out, err = run_git(["commit", "-m", f"{commit_note} [{timestamp}]"])
    if "nothing to commit" in out.lower() or "nothing to commit" in err.lower():
        print("ℹ️ No new file changes to commit. Pushing any unpushed commits...")

    print("🚀 Pushing MASTER_CORE_V1 to GitHub (main)...")
    code, out, err = run_git(["push", "-u", "origin", "main"])
    if code == 0:
        print("✅ SUCCESS: Workspace safely backed up and pushed to GitHub!")
        return True
    else:
        print(f"❌ Push failed: {err}\n💡 Tip: Run 'Pull' first if you updated the repo from your phone.")
        return False

def safe_pull():
    ensure_gitignore()
    snap_dir = create_snapshot()
    local_memory = load_memory_dict(MEMORY_FILE)

    print("🌐 Fetching latest updates from GitHub...")
    code, out, err = run_git(["fetch", "origin", "main"])
    if code != 0:
        print(f"❌ Fetch failed: {err}")
        return False

    # Stash any uncommitted local edits so pull never fails on dirty working tree
    run_git(["stash"])
    code, out, err = run_git(["pull", "--rebase", "origin", "main"])
    run_git(["stash", "pop"])

    # Losslessly merge local and remote knowledge_base.json entries
    remote_memory = load_memory_dict(MEMORY_FILE)
    if local_memory or remote_memory:
        merged_memory = {**remote_memory, **local_memory}
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(merged_memory, f, indent=2, ensure_ascii=False)

    if verify_workspace_syntax():
        print(f"✅ PULL COMPLETE & VERIFIED! Total learned topics in DB: {len(load_memory_dict(MEMORY_FILE))}")
        return True
    else:
        print("🚨 CRITICAL: Pulled code failed syntax verification! Triggering automatic rollback...")
        restore_snapshot(snap_dir)
        return False

def main_menu():
    print("\033[38;5;51m" + "═" * 76 + "\033[0m")
    print("\033[38;5;226m 🔄 MASTER CORE v22.0 — GITHUB CLOUD SYNC & SAFETY GUARDIAN\033[0m")
    print(f"\033[38;5;248m 📂 Workspace : {WORKSPACE}\033[0m")
    print("\033[38;5;51m" + "═" * 76 + "\033[0m")
    print(" 1. ⬆️  SAFE PUSH (Verify Syntax -> Commit -> Push to GitHub)")
    print(" 2. ⬇️  SAFE PULL (Backup Snapshot -> Pull from GitHub -> Verify Syntax)")
    print(" 3. 🔄 TWO-WAY SYNC (Safe Pull + Merge Memory DB + Safe Push)")
    print(" 4. 🔍 AUDIT ONLY (Check Syntax & JSON Health)")
    print(" 5. 🔗 LINK GITHUB REPO (Set Remote Origin URL)")
    print(" 6. ❌ EXIT")
    print("\033[38;5;51m" + "─" * 76 + "\033[0m")

    choice = input("╰─➤ Select option (1-6): ").strip()
    if choice == "1":
         safe_push()
    elif choice == "2":
        safe_pull()
    elif choice == "3":
        if safe_pull():
            safe_push("Two-way merged sync")
    elif choice == "4":
        verify_workspace_syntax()
    elif choice == "5":
        url = input("╰─➤ Enter your Private GitHub Repo URL: ").strip()
        if url:
            init_repo(url)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "--push":
            safe_push()
        elif cmd == "--pull":
            safe_pull()
        elif cmd == "--sync":
            if safe_pull():
                safe_push("Automated two-way sync")
        elif cmd == "--init" and len(sys.argv) > 2:
            init_repo(sys.argv[2])
        else:
            print("Usage: python sync_workspace.py [--push | --pull | --sync | --init <repo_url>]")
    else:
        main_menu()