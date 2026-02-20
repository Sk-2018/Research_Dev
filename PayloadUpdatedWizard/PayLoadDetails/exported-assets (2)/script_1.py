
# Fix the print statement
candidates = [
    "PayloadDiffViewer.exe", "GeminiPayloadDiff.exe",
    "payload_diff_viewer.py", "PayloadDiffViewer.py", 
    "GeminiPayloadDiff.py", "Test103.py"
]

print("✅ Created SimplePayloadLauncher.py")
print("\n" + "="*60)
print("SIMPLE PAYLOAD LAUNCHER CREATED")
print("="*60)
print("\nFile: SimplePayloadLauncher.py")
print("\nFeatures:")
print("• Simple GUI for selecting CSV/XLSX files")
print("• Auto-detects PayloadDiffViewer in the same folder")
print("• Tests different command-line arguments automatically")
print("• Falls back to default app if viewer not found")
print("• Real-time launch log")
print("\nTo use:")
print("1. Run: python SimplePayloadLauncher.py")
print("2. Click 'Browse' to select a CSV or XLSX file")
print("3. Click 'Launch Viewer' to test the integration")
print("\nViewer candidates searched:")
for candidate in candidates:
    print(f"  - {candidate}")
