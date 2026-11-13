#!/usr/bin/env python3
"""
MASTER AI DEVELOPMENT RUNNER
Cross-platform: Android Termux + Windows
Initial version: safe project inventory and development planning.
No cloud AI, no source-file modifications.
"""

import argparse
import datetime
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

EXCLUDED = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".master_dev", ".pytest_cache", ".mypy_cache"
}

IMPORTANT_NAMES = {
    "master_studio_agent.py",
    "core_backend.py",
    "voice_plugin.py",
    "pc_off_portable_runner.py",
    "mobile_remote_bridge.py",
    "agent_safety_adapter.py",
    "workstation_safety_bridge.py",
    "safe_file_ops.py",
    "recovery_ops.py",
}

PHASES = [
    "Project baseline and implementation roadmap",
    "Unified AI Core",
    "Shared Memory Service",
    "Unified Text and Voice Integration",
    "Local AI Engine Adapter (no cloud fallback)",
    "Safety and Approval Integration",
    "Tool Execution Manager",
    "Android Development Workflow",
    "Windows Workstation Integration",
    "GitHub Synchronization",
    "Integration Testing",
    "Final Documentation and Handover",
]


def run_readonly(command, cwd):
    try:
        result = subprocess.run(
            command, cwd=str(cwd), capture_output=True,
            text=True, timeout=15, shell=False
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except Exception as exc:
        return {"error": str(exc)}


def ignored(path):
    return any(part in EXCLUDED for part in path.parts)


def classify(path):
    name = path.name.lower()
    if name in IMPORTANT_NAMES:
        return "IMPORTANT_MODULE_REQUIRES_REVIEW"
    if name.endswith((".py", ".ps1", ".bat", ".sh", ".kt", ".cs")):
        return "SOURCE_CODE_REQUIRES_REVIEW"
    if name.endswith((".md", ".txt")):
        return "DOCUMENTATION"
    if name.endswith((".json", ".yaml", ".yml", ".toml", ".ini")):
        return "CONFIGURATION"
    return "OTHER"


def main():
    parser = argparse.ArgumentParser(
        description="Safe cross-platform MASTER AI development inventory"
    )
    parser.add_argument("--root", default=None)
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve() if args.root else Path(__file__).resolve().parent

    if not root.is_dir():
        raise SystemExit("ERROR: Project root does not exist.")

    if not (root / ".git").exists():
        print("WARNING: Git metadata not found in project root.")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output = root / ".master_dev" / "runs" / timestamp
    output.mkdir(parents=True, exist_ok=False)

    files = []
    for path in root.rglob("*"):
        if not path.is_file() or ignored(path.relative_to(root)):
            continue
        try:
            stat = path.stat()
            files.append({
                "path": path.relative_to(root).as_posix(),
                "size_bytes": stat.st_size,
                "category": classify(path),
            })
        except OSError:
            continue

    files.sort(key=lambda item: item["path"].lower())

    commands = {
        "python": shutil.which("python") or shutil.which("python3"),
        "git": shutil.which("git"),
        "ollama": shutil.which("ollama"),
        "llama_cli": shutil.which("llama-cli"),
        "llama_server": shutil.which("llama-server"),
    }

    git_status = None
    if commands["git"]:
        git_status = run_readonly(
            ["git", "status", "--short", "--branch"], root
        )

    safety_files = [
        "integration/agent_safety_adapter.py",
        "integration/workstation_safety_bridge.py",
        "safety/safe_file_ops.py",
        "safety/recovery_ops.py",
        "SAFETY_POLICY.md",
    ]

    safety_status = {
        name: (root / name).is_file() for name in safety_files
    }

    report = {
        "project": "MASTER AI WORKSTATION",
        "timestamp": timestamp,
        "root": str(root),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "mode": "READ_ONLY_INVENTORY_AND_PLANNING",
        "cloud_ai_used": False,
        "source_files_modified": False,
        "files": files,
        "file_count": len(files),
        "runtime_detection": commands,
        "git_status": git_status,
        "safety_components_present": safety_status,
        "implementation_phases": [
            {"number": i + 1, "name": phase, "status": "NOT_YET_VERIFIED"}
            for i, phase in enumerate(PHASES)
        ],
        "limitations": [
            "File presence does not prove functional completion.",
            "Local AI inference was not executed.",
            "No source files were modified.",
            "No cloud AI service was contacted.",
        ],
    }

    (output / "MODULE_STATUS.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    roadmap = [
        "# MASTER AI WORKSTATION — Development Roadmap",
        "",
        f"- Generated: {timestamp}",
        f"- Project root: `{root}`",
        "- Runner mode: Read-only inventory and planning",
        "- Cloud AI: Disabled",
        "",
        "## Implementation phases",
        "",
    ]
    for i, phase in enumerate(PHASES, 1):
        roadmap.append(f"{i}. [ ] {phase}")

    roadmap += [
        "",
        "## Safety",
        "",
        "- Back up every file before modification.",
        "- Require approval for high-risk changes.",
        "- Never bypass the real safety adapter.",
        "- Never overwrite existing files without authorization.",
        "",
        "## Important",
        "",
        "This inventory identifies files and dependencies; it does not",
        "claim that any feature is implemented or tested.",
        "Implementation requires a configured local AI backend and",
        "verified safety integration.",
    ]

    (output / "IMPLEMENTATION_ROADMAP.md").write_text(
        "\n".join(roadmap) + "\n", encoding="utf-8"
    )

    print("\nMASTER AI DEVELOPMENT RUNNER")
    print("Status: INVENTORY COMPLETED")
    print("Platform:", platform.system())
    print("Project:", root)
    print("Files discovered:", len(files))
    print("Cloud AI: NOT USED")
    print("Source files modified: NO")
    print("Git:", "available" if commands["git"] else "not found")
    print("\nReport folder:", output)
    print("Report: MODULE_STATUS.json")
    print("Roadmap: IMPLEMENTATION_ROADMAP.md")
    print("\nNext: review this report before enabling implementation.")


if __name__ == "__main__":
    main()
