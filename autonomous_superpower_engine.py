"""MASTER CORE V1 - Autonomous Superpower Engine.

First integration layer. Delegates development tasks to the existing
MasterSelfUpgradeRuntime and preserves its approval/safety workflow.
"""

import re

DEVELOPMENT_SIGNALS = (
    "self-upgrade:", "upgrade:", "develop:", "implement:",
    "build", "develop", "upgrade", "implement", "integrate",
    "create module", "fix my project", "improve master core",
    "autonomous agent", "নিজে তৈরি", "নিজেকে উন্নত",
    "উন্নত করো", "ইমপ্লিমেন্ট", "মডিউল তৈরি",
)

def is_development_request(prompt):
    if not isinstance(prompt, str) or not prompt.strip():
        return False

    value = prompt.strip().lower()

    explicit_prefixes = (
        "self-upgrade:", "upgrade:", "develop:", "implement:"
    )
    if value.startswith(explicit_prefixes):
        return True

    return any(signal in value for signal in DEVELOPMENT_SIGNALS[4:])

def dispatch(agent, prompt):
    """Return True when a development task was handed to the existing runtime."""
    if not is_development_request(prompt):
        return False

    print("\n\033[94m" + "=" * 68)
    print(" MASTER CORE — AUTONOMOUS DEVELOPMENT MODE")
    print("=" * 68 + "\033[0m")
    print("\033[96m[1/3] Development request identified.\033[0m")
    print("\033[96m[2/3] Handing task to existing safety-aware runtime.\033[0m")

    runner = getattr(agent, "run_self_upgrade", None)
    if not callable(runner):
        raise RuntimeError("Existing self-upgrade runtime is unavailable.")

    runner(prompt)

    print("\033[94m[3/3] Development task returned to Universal Prompt.\033[0m")
    return True
