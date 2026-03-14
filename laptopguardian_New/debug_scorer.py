import sys
import importlib.util

# Load the module directly from the file
spec = importlib.util.spec_from_file_location("scorer", "app/risk/scorer.py")
scorer = importlib.util.module_from_spec(spec)
sys.modules["app.risk.scorer"] = scorer

try:
    spec.loader.exec_module(scorer)
    print("Module loaded successfully")
    print("\nAvailable attributes:")
    for attr in dir(scorer):
        if not attr.startswith('_'):
            obj = getattr(scorer, attr)
            if callable(obj):
                print(f"  - {attr}() (function/class)")
            else:
                print(f"  - {attr} = {repr(obj)[:50]}")
                
    if hasattr(scorer, 'compute'):
        print("\n✓ 'compute' function found!")
    else:
        print("\n✗ 'compute' function NOT found!")
        
except Exception as e:
    print(f"Error loading module: {e}")
    import traceback
    traceback.print_exc()
