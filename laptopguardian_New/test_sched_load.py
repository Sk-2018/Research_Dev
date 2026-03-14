import sys
import importlib.util

# Load scheduler module directly from file
spec = importlib.util.spec_from_file_location("scheduler", "app/watchdog/scheduler.py")
sched = importlib.util.module_from_spec(spec)

try:
    spec.loader.exec_module(sched)
    print("✓ Scheduler loaded successfully")
    print(f"run_loop in dir: {'run_loop' in dir(sched)}")
    print(f"Public functions: {[n for n in dir(sched) if not n.startswith('_')]}")
except Exception as e:
    print(f"✗ Error loading scheduler: {e}")
    import traceback
    traceback.print_exc()
