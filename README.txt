MASTER CORE V1 SAFE FIX
For ~/master-core-v1 ONLY. Do not run in ~/MASTER_AI_MOBILE or Windows H: workspace.

Extract this ZIP into ~/master-core-v1, then run:
cd ~/master-core-v1
python master_core_targeted_fix.py

The installer checks the expected code layout, shows the changes, and waits for you to type APPLY.
It creates a timestamped backup and verifies SHA-256 before replacing only master_studio_agent.py.

Fixes:
- confines file reads/writes to the configured workspace
- blocks overwriting existing files through the simple file-task menu
- adds `search: your query` to the existing web-search functions

Does NOT configure local LLM inference. Web search requires internet and ddgs:
pip install ddgs
