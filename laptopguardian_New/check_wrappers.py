import os, glob

files_with_wrapper = []
for f in glob.glob('app/**/*.py', recursive=True) + glob.glob('tests/**/*.py', recursive=True):
    with open(f, 'r', errors='ignore') as file:
        content = file.read()
        if content.startswith("@'") or "'@ | Out-File" in content:
            files_with_wrapper.append(f)

if files_with_wrapper:
    print(f"⚠ Found {len(files_with_wrapper)} file(s) with PowerShell wrappers:")
    for f in files_with_wrapper:
        print(f'  - {f}')
else:
    print('✓ No PowerShell wrappers found in any files')
