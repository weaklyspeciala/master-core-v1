#!/usr/bin/env python3
"""MASTER CORE - Autonomous Quality Gate V1
Static validation only. Does not import or execute project modules.
"""

import ast
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT.parent / "config.json"

EXCLUDED_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".master_repair_backups", ".master_self_upgrade_backups",
    "repair_files"
}
EXCLUDED_FILES = {"patch_raw.py"}

errors = []
warnings = []
passed = 0


def report_error(message):
    errors.append(message)
    print("[FAIL]", message)


def report_warning(message):
    warnings.append(message)
    print("[WARN]", message)


def report_pass(message):
    global passed
    passed += 1
    print("[PASS]", message)


def validate_python():
    count = 0

    for current, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)

        for filename in sorted(files):
            if not filename.endswith(".py"):
                continue
            if filename in EXCLUDED_FILES:
                continue

            path = Path(current) / filename
            count += 1

            try:
                source = path.read_text(encoding="utf-8-sig")
                ast.parse(source, filename=str(path))
                report_pass(f"Python syntax: {path.relative_to(ROOT)}")
            except (SyntaxError, UnicodeError, OSError) as exc:
                report_error(f"Python: {path.relative_to(ROOT)}: {exc}")

    print(f"\nPython files checked: {count}")


def validate_json():
    count = 0

    for current, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)

        for filename in sorted(files):
            if not filename.endswith(".json"):
                continue

            path = Path(current) / filename
            count += 1

            try:
                with path.open("r", encoding="utf-8-sig") as handle:
                    json.load(handle)
                report_pass(f"JSON: {path.relative_to(ROOT)}")
            except (json.JSONDecodeError, UnicodeError, OSError) as exc:
                report_error(f"JSON: {path.relative_to(ROOT)}: {exc}")

    print(f"\nJSON files checked: {count}")


def validate_required_files():
    required = [
        "master_studio_agent.py",
        "master_self_upgrade_runtime.py",
        "staging/self_development_controller_v1.py",
        "integration/agent_safety_adapter.py",
        "SAFETY_POLICY.md",
        "README.md",
    ]

    for name in required:
        if (ROOT / name).is_file():
            report_pass(f"Required file: {name}")
        else:
            report_error(f"Required file missing: {name}")


def validate_config():
    if not CONFIG.is_file():
        report_error(f"Trusted config missing: {CONFIG}")
        return

    try:
        with CONFIG.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)

        roots = data.get("project_roots", [])
        if not isinstance(roots, list):
            report_error("config.json: project_roots must be a list")
            return

        resolved = []
        for item in roots:
            if isinstance(item, str):
                candidate = Path(item).expanduser().resolve()
                if candidate.is_dir():
                    resolved.append(candidate)

        if ROOT.resolve() in resolved:
            report_pass("Trusted project root is configured")
        else:
            report_error("MASTER CORE root is not in config.json project_roots")

    except (json.JSONDecodeError, OSError, TypeError) as exc:
        report_error(f"Trusted config: {exc}")


def main():
    print("=" * 58)
    print("MASTER CORE - AUTONOMOUS QUALITY GATE V1")
    print("=" * 58)
    print("Project:", ROOT)
    print("Mode: STATIC VALIDATION - NO PROJECT MODULE EXECUTION")
    print("-" * 58)

    if not ROOT.is_dir():
        print("[FATAL] Project root not found.")
        return 2

    validate_required_files()
    validate_config()
    validate_python()
    validate_json()

    print("\n" + "=" * 58)
    print("QUALITY GATE SUMMARY")
    print("=" * 58)
    print("PASSED :", passed)
    print("FAILED :", len(errors))
    print("WARNINGS:", len(warnings))

    if errors:
        print("\nRESULT: FAILED - FIX REQUIRED")
        print("No project files were modified.")
        return 1

    print("\nRESULT: PASSED - STATIC CHECKS SUCCESSFUL")
    print("No project files were modified.")
    print("Note: Syntax validation does not prove runtime correctness.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
