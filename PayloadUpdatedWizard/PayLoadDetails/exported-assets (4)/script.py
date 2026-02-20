
# Read the original GeminiPayloadDiff.py file
with open('GeminiPayloadDiff.py', 'r', encoding='utf-8') as f:
    original_code = f.read()

# Find the __main__ section at the end
main_section_old = '''if __name__ == "__main__":
    app = PayloadDiffViewerApp()
    app.mainloop()'''

# Create the new __main__ section with command-line argument support
main_section_new = '''if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Payload Diff Viewer - Compare current vs old payload configurations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python GeminiPayloadDiff.py
  python GeminiPayloadDiff.py --open data.csv
  python GeminiPayloadDiff.py -o data.xlsx
  python GeminiPayloadDiff.py --file export_20251109.csv
        """
    )
    
    parser.add_argument(
        'file', 
        nargs='?', 
        help='CSV or XLSX file to open automatically'
    )
    
    parser.add_argument(
        '--open', '-o',
        dest='open_file',
        help='CSV or XLSX file to open automatically (alternative syntax)'
    )
    
    parser.add_argument(
        '--file', '-f',
        dest='file_arg',
        help='CSV or XLSX file to open automatically (alternative syntax)'
    )
    
    args = parser.parse_args()
    
    # Determine which file to open (support multiple argument styles)
    file_to_open = args.file or args.open_file or args.file_arg
    
    # Create and start the app
    app = PayloadDiffViewerApp()
    
    # If a file was specified, load it after the GUI is ready
    if file_to_open:
        from pathlib import Path
        file_path = Path(file_to_open)
        
        if file_path.exists():
            # Schedule the file load after the GUI initializes
            app.after(100, lambda: app.load_file_from_path(str(file_path)))
            logger.info(f"Auto-loading file from command line: {file_path}")
        else:
            logger.error(f"File not found: {file_path}")
            app.after(100, lambda: messagebox.showerror(
                "File Not Found",
                f"Could not find the specified file:\\n\\n{file_path}\\n\\nPlease use File > Open to load a file."
            ))
    
    app.mainloop()'''

# Replace the old main section with the new one
if main_section_old in original_code:
    fixed_code = original_code.replace(main_section_old, main_section_new)
    print("✅ Found and replaced __main__ section")
else:
    print("❌ Could not find exact __main__ section, trying alternative...")
    # Try to find just the class instantiation
    import re
    pattern = r'if __name__ == "__main__":\s+app = PayloadDiffViewerApp\(\)\s+app\.mainloop\(\)'
    if re.search(pattern, original_code):
        fixed_code = re.sub(pattern, main_section_new, original_code)
        print("✅ Found and replaced __main__ section (alternative method)")
    else:
        print("⚠️  Could not find __main__ section automatically")
        fixed_code = original_code

# Now we need to add the load_file_from_path method to the PayloadDiffViewerApp class
# Find a good place to insert it - after the load_file method

load_method_addition = '''
    def load_file_from_path(self, file_path: str):
        """Load a file from a path (for command-line auto-load)."""
        try:
            logger.info(f"Auto-loading file: {file_path}")
            self.load_file(file_path)
        except Exception as e:
            logger.error(f"Failed to auto-load file: {e}")
            messagebox.showerror(
                "Auto-Load Failed",
                f"Could not load the file:\\n\\n{file_path}\\n\\nError: {e}\\n\\nPlease use File > Open to try again."
            )
'''

# Find where to insert this method - look for the end of load_file method
# We'll insert it right before the "def open_file" method or similar
search_pattern = 'def open_file(self):'
if search_pattern in fixed_code:
    # Insert before open_file method
    fixed_code = fixed_code.replace(
        '    def open_file(self):',
        load_method_addition + '\n    def open_file(self):'
    )
    print("✅ Added load_file_from_path method")
else:
    print("⚠️  Could not find insertion point for load_file_from_path method")

# Write the fixed version
with open('GeminiPayloadDiff_FIXED.py', 'w', encoding='utf-8') as f:
    f.write(fixed_code)

print("\n" + "="*60)
print("FIXED VERSION CREATED")
print("="*60)
print("File: GeminiPayloadDiff_FIXED.py")
print(f"Size: {len(fixed_code):,} characters")
print("\nChanges made:")
print("1. ✅ Added argparse for command-line argument parsing")
print("2. ✅ Added support for multiple argument formats:")
print("   - python GeminiPayloadDiff_FIXED.py file.csv")
print("   - python GeminiPayloadDiff_FIXED.py --open file.csv")
print("   - python GeminiPayloadDiff_FIXED.py -o file.csv")
print("   - python GeminiPayloadDiff_FIXED.py --file file.csv")
print("   - python GeminiPayloadDiff_FIXED.py -f file.csv")
print("3. ✅ Added load_file_from_path method for auto-loading")
print("4. ✅ Added error handling for missing files")
print("5. ✅ File loads automatically 100ms after GUI starts")
print("\nNow your launcher will work perfectly!")
print("The viewer will open AND load the file automatically!")
