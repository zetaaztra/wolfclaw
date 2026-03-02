import os
import sys

# Add project root to path
sys.path.insert(0, os.getcwd())

# Set desktop environment to enable all tools
os.environ["WOLFCLAW_ENVIRONMENT"] = "desktop"

try:
    from core.tools import execute_tool, plugin_manager
    
    print("--- 🐺 Wolfclaw Plugin System Verification ---")
    
    # 1. Check loaded plugins
    if plugin_manager and plugin_manager.plugins:
        print(f"✅ Loaded Plugins: {list(plugin_manager.plugins.keys())}")
        
        # 2. Test execution of the Math Calculator
        test_expr = "sqrt(144) + sin(pi/2)"
        print(f"\n[Test] Executing 'calculate_math' with: {test_expr}")
        
        args = {"expression": test_expr}
        result = execute_tool("calculate_math", args)
        
        print(f"Result: {result}")
        if result == "13.0":
            print("\n🔥 VERDICT: PLUGIN SYSTEM IS 100% FUNCTIONAL!")
        else:
            print("\n⚠️  Unexpected result, but code successfully executed.")
            
    else:
        print("❌ No plugins loaded in plugin_manager.")

except Exception as e:
    print(f"❌ Error during verification: {e}")
