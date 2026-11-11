import sys
from pathlib import Path
import importlib.util

print("\n\033[96m=== DEPENDENCY INJECTION ISOLATION TEST ===\033[0m")

# 1. Load the controller dynamically
controller_path = Path("H:/MASTER_AI_WORKSTATION/MASTER_AI_WORKSTATION/MASTER_CORE_V1/staging/self_development_controller_v1.py")
spec = importlib.util.spec_from_file_location("sdc", controller_path)
sdc = importlib.util.module_from_spec(spec)
sys.modules["sdc"] = sdc
spec.loader.exec_module(sdc)

# 2. Mock the Main Agent's secure namespace
mock_namespace = {
    "_MASTER_AGENT_SAFETY_INSTALLED": True,
    "tool_tree": lambda args, proj: print("Mock Tree Called"),
    "tool_read": lambda args, proj: print("Mock Read Called"),
    "tool_write": lambda args, proj: {"ok": True, "status": "pending_approval"},
    "tool_check": lambda args, proj: print("Mock Check Called"),
    "ollama": lambda messages: print("Mock Ollama Called")
}

try:
    # 3. Try to initialize using the factory method or direct init
    controller = None
    if hasattr(sdc.SelfDevelopmentController, 'from_agent_namespace'):
        print("\033[93m[INFO]\033[0m Found 'from_agent_namespace' factory method.")
        controller = sdc.SelfDevelopmentController.from_agent_namespace(mock_namespace, "H:/MASTER_AI_WORKSTATION/MASTER_AI_WORKSTATION")
    else:
        print("\033[93m[INFO]\033[0m Factory method not found, using direct __init__.")
        controller = sdc.SelfDevelopmentController(mock_namespace, "H:/MASTER_AI_WORKSTATION/MASTER_AI_WORKSTATION")
        
    print("\033[92m[SUCCESS]\033[0m Controller initialized safely!")
    
    # 4. Verify it captured the callbacks
    if hasattr(controller, 'callbacks'):
        print(f"\033[92m[SUCCESS]\033[0m Captured Callbacks: {list(controller.callbacks.keys())}")
    else:
        print("\033[91m[FAIL]\033[0m Callbacks dictionary not found in controller instance.")

except Exception as e:
    print(f"\033[91m[FATAL ERROR]\033[0m Initialization crashed: {str(e)}")
print("\033[96m===========================================\033[0m\n")
