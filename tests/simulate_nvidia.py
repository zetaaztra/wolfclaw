import os
import sys

# Setup environment to emulate desktop runtime
os.environ['WOLFCLAW_ENVIRONMENT'] = "desktop"
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.config import set_key, get_current_user_id
from core.llm_engine import WolfEngine

def run_simulation():
    print("1. Injecting API Key into Security Layer...")
    # Let the config module use its own default user_id logic so WolfEngine can read it properly
    # Use the key from environment if available, otherwise use a placeholder for the user to fill
    nv_key = os.getenv("NVIDIA_API_KEY", "YOUR_NVIDIA_API_KEY_HERE")
    if nv_key == "YOUR_NVIDIA_API_KEY_HERE":
        print("   ⚠️  No NVIDIA_API_KEY found in environment. Using placeholder (simulation may fail).")
    try:
        set_key("nvidia", nv_key)
        print("   ✅ Nvidia Key saved successfully in local config.\n")
    except Exception as e:
        print(f"   ❌ Failed to save key: {e}")
        return

    print("2. Spawning Wolfclaw Fleet Agent...")
    
    # Mock heartbeat so simulation isn't blocked by user mouse movement
    import core.heartbeat as hb
    hb.heartbeat.is_safe_to_execute = lambda: True
    
    model_name = "nvidia/meta/llama-3.1-70b-instruct"
    engine = WolfEngine(model_name)
    
    print("   🤖 Commander Beta spawned. Establishing connection to Nvidia NIM framework...")
    messages = [
        {"role": "system", "content": "You are the Wolfclaw Operations Commander. Speak directly and confidently. Keep it brief. No pleasantries. Acknowledge that your intelligence core is powered by the new Nvidia API."},
        {"role": "user", "content": "Commander, the new Nvidia keys are authenticated. Please provide a system operational report."}
    ]
    
    print("\n   [Uplink to meta/llama-3.1-405b-instruct initiated...]")
    try:
        response_obj = engine.chat(messages)
        response = response_obj.get('content', str(response_obj))
        print("\n" + "="*50)
        print(" TRANSMISSION RECEIVED")
        print("="*50)
        print(response)
        print("="*50 + "\n")
        print("✅ Fleet Simulation: 100% SUCCESS!")
    except Exception as e:
        print("\n❌ Fleet Simulation FAILED. Engine Error:")
        print(str(e))

if __name__ == "__main__":
    run_simulation()
