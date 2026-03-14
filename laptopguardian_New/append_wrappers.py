# Read current scorer.py
with open('app/risk/scorer.py', 'r') as f:
    current_content = f.read()

# Read wrapper code
with open('scorer_wrappers.py', 'r') as f:
    wrapper_code = f.read()

# Append wrapper code
new_content = current_content + wrapper_code

# Write back
with open('app/risk/scorer.py', 'w') as f:
    f.write(new_content)

print("✓ Wrapper code appended to scorer.py")
