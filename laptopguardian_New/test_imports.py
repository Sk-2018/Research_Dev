# Try to import just the imports from scheduler
try:
    print("Loading imports...")
    import time, logging, threading
    print("✓ time, logging, threading")
    
    from app.collector import collect_all
    print("✓ collect_all")
    
    from app.risk.scorer import compute as score_risk, TIER_WARN, TIER_CRITICAL
    print("✓ risk scorer")
    
    from app.watchdog.actions import (
        switch_to_power_saver, restore_power_plan,
        lower_process_priority, toast_notification,
        request_process_termination
    )
    print("✓ actions")
    
    print("\nAll imports successful!")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
