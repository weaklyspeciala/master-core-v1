MASTER CORE V1 — GUARDED SELF-UPGRADE BRIDGE

WHAT THIS PACKAGE DOES
- Integrates the existing staging/self_development_controller_v1.py with the existing MasterSystemAgent.
- Adds explicit commands: upgrade: <task>, develop: <task>, self-upgrade: <task>.
- Uses the existing integration/agent_safety_adapter.py to create approval tickets.
- Does NOT apply code changes automatically.
- Uses only a local OpenAI-compatible llama.cpp endpoint at 127.0.0.1:8080.
- Does NOT use cloud AI or cloud fallback.
- Web research is disabled in this bridge.

INSTALLATION
1. Extract this package into the ROOT of the Termux repository ~/master-core-v1 (merge folders; do not replace existing folders wholesale).
2. Confirm these existing files remain present:
   master_studio_agent.py
   staging/self_development_controller_v1.py
   integration/agent_safety_adapter.py
3. Run: python install_master_self_upgrade.py
4. Read the displayed target, then type APPLY only if it is correct.

SAFETY
- Installer backs up master_studio_agent.py and verifies SHA256 before editing.
- Installer aborts if expected source markers differ.
- Controller-generated code becomes a pending approval ticket only.
- Approval adapter requires trusted project roots in the parent config.json.
- If trusted roots are missing/mismatched, proposals are blocked; do not weaken safety to make it pass.
- Never use integration/agent_safety_adapter_v2.py (Auto-Approve variant).
- No Git push, reset, clean, or bulk staging is performed.

LOCAL MODEL
The bridge expects a local llama.cpp server compatible with /v1/chat/completions:
MASTER_LOCAL_LLM_URL=http://127.0.0.1:8080/v1/chat/completions
MASTER_LOCAL_LLM_MODEL=local-model

This package does not download model weights or compile llama.cpp automatically. That must be a separate device-aware step after checking Android RAM and free storage. The existing vocab-only GGUF files are not model weights.

IMPORTANT LIMITATION
The current controller's generated Python code is syntax-checked before a ticket is created, but it is not automatically executed. Keep this restriction until sandboxed tests and a recovery policy are implemented and verified.
