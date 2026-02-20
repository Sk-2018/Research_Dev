
# Let me find ALL method definitions in the PayloadDiffViewerApp class
with open('GeminiPayloadDiff.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the class definition and all its methods
in_class = False
methods = []

for i, line in enumerate(lines):
    if 'class PayloadDiffViewerApp' in line:
        in_class = True
        print(f"Found class at line {i+1}: {line.strip()}")
        continue
    
    if in_class:
        # Look for method definitions
        if line.strip().startswith('def '):
            method_name = line.strip().split('(')[0].replace('def ', '')
            methods.append((i+1, method_name))
        
        # End of class when we find another class or end of file
        if line.startswith('class ') and 'PayloadDiffViewerApp' not in line:
            break

print(f"\nFound {len(methods)} methods in PayloadDiffViewerApp class:")
print("\nSearching for file-related methods:")
for line_num, method in methods:
    if any(keyword in method.lower() for keyword in ['open', 'file', 'load', 'choose', 'select']):
        print(f"  Line {line_num}: {method}")
