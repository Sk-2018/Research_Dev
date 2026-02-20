
# Let me search for the actual __main__ section more carefully
with open('GeminiPayloadDiff.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the __main__ section
main_line_start = None
for i, line in enumerate(lines):
    if '__name__' in line and '__main__' in line:
        main_line_start = i
        break

if main_line_start:
    print(f"Found __main__ at line {main_line_start + 1}")
    print("\nCurrent code:")
    print("".join(lines[main_line_start:min(main_line_start+5, len(lines))]))
else:
    print("Could not find __main__ section")
    print(f"\nLast 20 lines of file:")
    print("".join(lines[-20:]))
