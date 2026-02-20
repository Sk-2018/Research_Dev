
# Read the file and find the complete __main__ section
with open('GeminiPayloadDiff.py', 'r', encoding='utf-8') as f:
    original_code = f.read()

# Show the last part to see the actual main block
lines = original_code.split('\n')
print("Last 30 lines of the file:")
print('\n'.join(lines[-30:]))
