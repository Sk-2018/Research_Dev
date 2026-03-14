with open('app/risk/scorer.py', 'r') as f:
    content = f.read()
    
print(f"File size: {len(content)} bytes")
print(f"Lines: {content.count(chr(10))}")
print(f"'def compute' in file: {'def compute' in content}")
print(f"'def _clamp' in file: {'def _clamp' in content}")
print()

# Check what's actually being imported
import sys
import importlib.util

# Remove any cached versions
for key in list(sys.modules.keys()):
    if 'app.risk' in key:
        del sys.modules[key]

# Load the module directly
spec = importlib.util.spec_from_file_location("scorer", "app/risk/scorer.py")
scorer_module = importlib.util.module_from_spec(spec)

try:
    spec.loader.exec_module(scorer_module)
    print("Module loaded successfully")
    print(f"Has 'compute': {hasattr(scorer_module, 'compute')}")
    print(f"Has '_clamp': {hasattr(scorer_module, '_clamp')}")
    print(f"Has 'calculate_risk_score': {hasattr(scorer_module, 'calculate_risk_score')}")
    
    # List all public functions
    print("\nPublic functions/classes:")
    for name in dir(scorer_module):
        if not name.startswith('_'):
            print(f"  - {name}")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
