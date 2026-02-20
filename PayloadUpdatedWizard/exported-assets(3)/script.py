
import ast
import re
from collections import defaultdict

# Comprehensive analysis of both files
files = {
    'NewPayloadUpdated_ENHANCED.py': 'Wizard/Export',
    'GeminiPayloadDiff.py': 'Viewer/Diff'
}

analysis_results = {}

for filename, file_type in files.items():
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Parse AST
    try:
        tree = ast.parse(content)
        
        # Collect statistics
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        functions = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        imports = [node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)]
        from_imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]
        
        # Code quality checks
        issues = {
            'hardcoded_credentials': [],
            'sql_injection_risks': [],
            'error_handling_gaps': [],
            'security_concerns': [],
            'performance_issues': [],
            'code_smells': []
        }
        
        # Check for hardcoded values
        for i, line in enumerate(lines, 1):
            lower_line = line.lower()
            
            # Hardcoded credentials
            if any(pattern in lower_line for pattern in ['password', 'pwd', 'pass']):
                if '=' in line and not line.strip().startswith('#'):
                    issues['hardcoded_credentials'].append((i, line.strip()[:80]))
            
            # SQL injection risks
            if 'execute' in lower_line or 'query' in lower_line:
                if '+' in line or 'format(' in line or 'f"' in line or "f'" in line:
                    issues['sql_injection_risks'].append((i, line.strip()[:80]))
            
            # Missing error handling
            if 'open(' in line or 'connect(' in line:
                # Check if within try block
                if not any('try:' in lines[max(0,i-5):i]):
                    issues['error_handling_gaps'].append((i, line.strip()[:80]))
            
            # Performance issues
            if 'for ' in line and 'pd.concat' in lines[i] if i < len(lines) else False:
                issues['performance_issues'].append((i, 'Potential DataFrame concat in loop'))
        
        # Security analysis
        security_patterns = {
            'eval': r'\beval\(',
            'exec': r'\bexec\(',
            'pickle': r'\bpickle\.',
            'shell': r'shell\s*=\s*True',
        }
        
        for pattern_name, pattern in security_patterns.items():
            if re.search(pattern, content):
                issues['security_concerns'].append(f"Found {pattern_name} usage")
        
        # Code complexity
        long_functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_lines = len(ast.unparse(node).split('\n'))
                if func_lines > 50:
                    long_functions.append((node.name, func_lines))
        
        if long_functions:
            issues['code_smells'].append(f"Long functions (>50 lines): {long_functions}")
        
        analysis_results[filename] = {
            'type': file_type,
            'lines': len(lines),
            'classes': len(classes),
            'functions': len(functions),
            'imports': len(imports) + len(from_imports),
            'class_names': classes[:5],
            'issues': issues
        }
        
    except SyntaxError as e:
        analysis_results[filename] = {'error': str(e)}

# Print comprehensive analysis
print("=" * 80)
print("COMPREHENSIVE CODE ANALYSIS")
print("=" * 80)

for filename, data in analysis_results.items():
    print(f"\n{'='*80}")
    print(f"FILE: {filename} ({data.get('type', 'Unknown')})")
    print(f"{'='*80}")
    
    if 'error' in data:
        print(f"ERROR: {data['error']}")
        continue
    
    print(f"\n📊 CODE METRICS:")
    print(f"  • Lines of Code: {data['lines']}")
    print(f"  • Classes: {data['classes']}")
    print(f"  • Functions/Methods: {data['functions']}")
    print(f"  • Import Statements: {data['imports']}")
    print(f"  • Main Classes: {', '.join(data['class_names'])}")
    
    print(f"\n🔍 ISSUES DETECTED:")
    
    for issue_type, issue_list in data['issues'].items():
        if issue_list:
            print(f"\n  ⚠️  {issue_type.replace('_', ' ').title()}:")
            if isinstance(issue_list, list):
                for item in issue_list[:3]:  # Limit to 3 items
                    if isinstance(item, tuple):
                        print(f"      Line {item[0]}: {item[1]}")
                    else:
                        print(f"      {item}")
                if len(issue_list) > 3:
                    print(f"      ... and {len(issue_list) - 3} more")
            else:
                print(f"      {issue_list}")

# Summary recommendations
print(f"\n{'='*80}")
print("PRIORITY RECOMMENDATIONS")
print(f"{'='*80}")

recommendations = [
    "1. SECURITY: Externalize all hardcoded credentials to environment variables (.env file)",
    "2. SQL SAFETY: Replace string formatting in SQL queries with parameterized queries",
    "3. ERROR HANDLING: Add try-except blocks around all file/network operations",
    "4. PERFORMANCE: Avoid DataFrame concatenation in loops; use list append + single concat",
    "5. CODE QUALITY: Break down functions >50 lines into smaller, testable units",
    "6. LOGGING: Replace print statements with structured logging (logging module)",
    "7. VALIDATION: Add input validation for all user-supplied data",
    "8. DOCUMENTATION: Add docstrings to all classes and public methods",
    "9. TESTING: Implement unit tests with pytest (stubs provided in v2)",
    "10. CONFIGURATION: Move all hardcoded configs to external YAML/JSON files"
]

for rec in recommendations:
    print(rec)

print(f"\n{'='*80}")
print("ANALYSIS COMPLETE")
print(f"{'='*80}")
