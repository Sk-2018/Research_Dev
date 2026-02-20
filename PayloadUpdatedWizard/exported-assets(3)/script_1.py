
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
            'hardcoded_values': [],
            'sql_patterns': [],
            'long_functions': [],
            'security_patterns': [],
            'deprecated_usage': []
        }
        
        # Check for hardcoded values
        for i, line in enumerate(lines, 1):
            lower_line = line.lower()
            
            # Hardcoded database configs
            if '"host' in line or '"port' in line or '"dbname' in line:
                if not line.strip().startswith('#'):
                    issues['hardcoded_values'].append((i, line.strip()[:80]))
            
            # SQL patterns
            if 'execute' in lower_line and ('f"' in line or "f'" in line or '+' in line):
                issues['sql_patterns'].append((i, line.strip()[:80]))
            
            # Deprecated patterns
            if 'print(' in line and not line.strip().startswith('#'):
                issues['deprecated_usage'].append((i, 'print statement (use logging)'))
        
        # Check function length
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                try:
                    func_source = ast.get_source_segment(content, node)
                    if func_source:
                        func_lines = len(func_source.split('\n'))
                        if func_lines > 50:
                            issues['long_functions'].append((node.name, func_lines))
                except:
                    pass
        
        # Security patterns
        security_checks = [
            ('eval/exec usage', r'\b(eval|exec)\('),
            ('shell=True', r'shell\s*=\s*True'),
            ('pickle usage', r'\bpickle\.'),
        ]
        
        for check_name, pattern in security_checks:
            if re.search(pattern, content):
                issues['security_patterns'].append(check_name)
        
        analysis_results[filename] = {
            'type': file_type,
            'lines': len(lines),
            'classes': len(classes),
            'functions': len(functions),
            'imports': len(imports) + len(from_imports),
            'class_names': classes[:5],
            'function_names': functions[:10],
            'issues': issues
        }
        
    except SyntaxError as e:
        analysis_results[filename] = {'error': str(e)}

# Print comprehensive analysis
print("=" * 80)
print("COMPREHENSIVE CODE ANALYSIS REPORT")
print("=" * 80)

for filename, data in analysis_results.items():
    print(f"\n{'='*80}")
    print(f"FILE: {filename}")
    print(f"TYPE: {data.get('type', 'Unknown')}")
    print(f"{'='*80}")
    
    if 'error' in data:
        print(f"SYNTAX ERROR: {data['error']}")
        continue
    
    print(f"\n📊 CODE METRICS:")
    print(f"  ├─ Total Lines: {data['lines']}")
    print(f"  ├─ Classes: {data['classes']}")
    print(f"  ├─ Functions/Methods: {data['functions']}")
    print(f"  └─ Imports: {data['imports']}")
    
    if data['class_names']:
        print(f"\n📦 MAIN CLASSES:")
        for cls in data['class_names']:
            print(f"  • {cls}")
    
    if data['function_names']:
        print(f"\n⚙️  KEY FUNCTIONS (first 10):")
        for func in data['function_names'][:10]:
            print(f"  • {func}")
    
    print(f"\n🔍 DETECTED ISSUES:")
    
    total_issues = sum(len(v) if isinstance(v, list) else 1 for v in data['issues'].values() if v)
    
    if total_issues == 0:
        print("  ✅ No major issues detected")
    else:
        for issue_type, issue_list in data['issues'].items():
            if issue_list:
                issue_name = issue_type.replace('_', ' ').title()
                print(f"\n  ⚠️  {issue_name} ({len(issue_list)} found):")
                
                if isinstance(issue_list, list):
                    display_count = min(3, len(issue_list))
                    for item in issue_list[:display_count]:
                        if isinstance(item, tuple) and len(item) == 2:
                            print(f"      Line {item[0]}: {item[1]}")
                        else:
                            print(f"      {item}")
                    
                    if len(issue_list) > display_count:
                        print(f"      ... and {len(issue_list) - display_count} more instances")

# Overall summary
print(f"\n{'='*80}")
print("OVERALL ASSESSMENT")
print(f"{'='*80}")

total_lines = sum(d.get('lines', 0) for d in analysis_results.values())
total_classes = sum(d.get('classes', 0) for d in analysis_results.values())
total_functions = sum(d.get('functions', 0) for d in analysis_results.values())

print(f"\n📈 PROJECT STATISTICS:")
print(f"  • Total Lines: {total_lines}")
print(f"  • Total Classes: {total_classes}")
print(f"  • Total Functions: {total_functions}")
print(f"  • Files Analyzed: {len(analysis_results)}")

print(f"\n⭐ CODE QUALITY SCORE:")
# Simple scoring
score = 100
for data in analysis_results.values():
    if 'issues' in data:
        score -= len(data['issues'].get('hardcoded_values', [])) * 2
        score -= len(data['issues'].get('sql_patterns', [])) * 3
        score -= len(data['issues'].get('long_functions', [])) * 1
        score -= len(data['issues'].get('security_patterns', [])) * 5
        score -= len(data['issues'].get('deprecated_usage', [])) * 0.5

score = max(0, min(100, score))
print(f"  Overall Score: {score:.1f}/100")

if score >= 80:
    rating = "Excellent ✅"
elif score >= 60:
    rating = "Good 👍"
elif score >= 40:
    rating = "Fair ⚠️"
else:
    rating = "Needs Improvement 🔧"

print(f"  Rating: {rating}")

print(f"\n{'='*80}")
