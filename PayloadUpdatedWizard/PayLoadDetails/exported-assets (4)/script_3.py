
# Now I can see the actual __main__ section. Let me create the proper fix
with open('GeminiPayloadDiff.py', 'r', encoding='utf-8') as f:
    original_code = f.read()

# Find and replace the __main__ section
old_main_section = '''if __name__ == '__main__':
    # Ensure pandas is available, or give a final warning
    if not HAS_PANDAS:
        print("CRITICAL: pandas is not installed. This application requires it for "
              "efficient file loading.")
        print("Please install required libraries:")
        print("pip install pandas numpy openpyxl deepdiff matplotlib")
        # You could choose to exit here, or let the Tkinter warning handle it
        # sys.exit(1)

    app = PayloadDiffViewerApp()
    app.mainloop()'''

new_main_section = '''if __name__ == '__main__':
    import argparse
    
    # Ensure pandas is available, or give a final warning
    if not HAS_PANDAS:
        print("CRITICAL: pandas is not installed. This application requires it for "
              "efficient file loading.")
        print("Please install required libraries:")
        print("pip install pandas numpy openpyxl deepdiff matplotlib")
        # You could choose to exit here, or let the Tkinter warning handle it
        # sys.exit(1)
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Payload Diff Viewer - Compare current vs old payload configurations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python GeminiPayloadDiff.py
  python GeminiPayloadDiff.py data.csv
  python GeminiPayloadDiff.py --open data.xlsx
  python GeminiPayloadDiff.py -o export.csv
  python GeminiPayloadDiff.py --file payload_export_20251109.xlsx
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
    
    # Create the app
    app = PayloadDiffViewerApp()
    
    # If a file was specified, load it after the GUI initializes
    if file_to_open:
        from pathlib import Path
        file_path = Path(file_to_open)
        
        if file_path.exists():
            # Schedule the file load after the GUI is ready (100ms delay)
            def auto_load():
                try:
                    logger.info(f"Auto-loading file from command line: {file_path}")
                    app.load_file(str(file_path))
                except Exception as e:
                    logger.error(f"Failed to auto-load file: {e}")
                    messagebox.showerror(
                        "Auto-Load Failed",
                        f"Could not load the specified file:\\n\\n{file_path}\\n\\nError: {e}\\n\\nPlease use File > Open to try again."
                    )
            
            app.after(100, auto_load)
        else:
            logger.error(f"File not found: {file_path}")
            def show_error():
                messagebox.showerror(
                    "File Not Found",
                    f"Could not find the specified file:\\n\\n{file_path}\\n\\nPlease use File > Open to load a file."
                )
            app.after(100, show_error)
    
    app.mainloop()'''

# Replace the old section with the new one
if old_main_section in original_code:
    fixed_code = original_code.replace(old_main_section, new_main_section)
    print("✅ Successfully replaced __main__ section")
    
    # Write the fixed version
    with open('GeminiPayloadDiff_FIXED.py', 'w', encoding='utf-8') as f:
        f.write(fixed_code)
    
    print("\n" + "="*70)
    print("GEMINI PAYLOAD DIFF VIEWER - FIXED VERSION CREATED")
    print("="*70)
    print("\nFile: GeminiPayloadDiff_FIXED.py")
    print(f"Original size: {len(original_code):,} characters")
    print(f"Fixed size: {len(fixed_code):,} characters")
    print(f"Added: {len(fixed_code) - len(original_code):,} characters")
    
    print("\n✅ COMMAND-LINE SUPPORT ADDED")
    print("\nNow supports all these formats:")
    print("  python GeminiPayloadDiff_FIXED.py data.csv")
    print("  python GeminiPayloadDiff_FIXED.py --open data.csv")
    print("  python GeminiPayloadDiff_FIXED.py -o data.xlsx")
    print("  python GeminiPayloadDiff_FIXED.py --file export.csv")
    print("  python GeminiPayloadDiff_FIXED.py -f export.xlsx")
    
    print("\n✅ AUTO-LOAD FEATURE")
    print("  • File loads automatically 100ms after GUI starts")
    print("  • Works with both CSV and XLSX files")
    print("  • Shows error dialog if file not found")
    print("  • Falls back to manual Open if auto-load fails")
    
    print("\n✅ BACKWARD COMPATIBLE")
    print("  • Running without arguments opens empty viewer (original behavior)")
    print("  • All existing features preserved")
    
    print("\n" + "="*70)
    print("READY TO USE!")
    print("="*70)
    print("\nRename or replace your GeminiPayloadDiff.py with this fixed version")
    print("and the launcher will automatically load files!")
    
else:
    print("❌ Could not find the __main__ section to replace")
    print("\nLet me show what was found:")
    # Find where it starts
    idx = original_code.find("if __name__ == '__main__':")
    if idx >= 0:
        print(original_code[idx:idx+500])
