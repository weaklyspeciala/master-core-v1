MASTER AI ONE-SHOT REPAIR

This package repairs the four Termux runtime files in one installer run.
It uses the existing project as the target; do not extract over the project manually.

After extracting this ZIP into ~/master-core-v1 (without overwriting anything), run:
python install_repair.py

The installer lists its exact scope and requires typing APPLY. It creates a timestamped backup, verifies SHA256 hashes, stages files, compiles them, then atomically installs.

Important limitation: this repair disables forced web/cloud AI calls and failed-memory writes, and routes Text and Voice through the same MasterSystemAgent. It does not magically add an LLM. A supported local model/runtime must be installed and configured separately for generative reasoning. Arbitrary shell execution and unrestricted file overwrites are intentionally not enabled.
