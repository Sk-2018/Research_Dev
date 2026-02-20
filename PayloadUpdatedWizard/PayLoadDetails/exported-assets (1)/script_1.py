
# Recreate the complete fixed code
with open('NewPaylaodUpdated102.py', 'r', encoding='utf-8') as f:
    original_code = f.read()

fixed_code = original_code

# Apply all fixes
import re

# 1. Fix CANDIDATES list
pattern = r'CANDIDATES = \[\s*"PayloadDiffViewer\.exe","GeminiPayloadDiff\.exe",\s*"payload_diff_viewer\.py","PayloadDiffViewer\.py","GeminiPayloadDiff\.py","Test103\.py"\s*(?=\n)'
replacement = '''CANDIDATES = [
    "PayloadDiffViewer.exe", "GeminiPayloadDiff.exe",
    "payload_diff_viewer.py", "PayloadDiffViewer.py", "GeminiPayloadDiff.py", "Test103.py"
]'''
fixed_code = re.sub(pattern, replacement, fixed_code)

# 2. Add constants after APP_VERSION
old_header = 'APP_VERSION = "1.3.2-wizard"\nHERE = Path(__file__).resolve().parent'
new_header = '''APP_VERSION = "1.3.3-wizard-fixed"
HERE = Path(__file__).resolve().parent

# Connection and timeout constants
STATEMENT_TIMEOUT_MS = 120000  # 2 minutes
IDLE_SESSION_TIMEOUT_MS = 60000  # 1 minute
CONNECTION_TIMEOUT_SEC = 8
CONNECT_RETRY_DELAYS = [0, 3, 6, 10]  # seconds
MAX_QUERY_LOG_LENGTH = 2000  # characters'''
fixed_code = fixed_code.replace(old_header, new_header)

# 3. Update connect_pg to use constants
fixed_code = fixed_code.replace(
    'options = "-c statement_timeout=120000 -c idle_in_transaction_session_timeout=60000"',
    'options = f"-c statement_timeout={STATEMENT_TIMEOUT_MS} -c idle_in_transaction_session_timeout={IDLE_SESSION_TIMEOUT_MS}"'
)

# 4. Update retry delays
fixed_code = fixed_code.replace('for wait in [0, 3, 6, 10]:', 'for wait in CONNECT_RETRY_DELAYS:')

# 5. Update sanitize function
fixed_code = fixed_code.replace(
    'def sanitize_sql_for_log(sql: str, maxlen: int = 2000) -> str:',
    'def sanitize_sql_for_log(sql: str, maxlen: int = MAX_QUERY_LOG_LENGTH) -> str:'
)

# 6. Update connection timeout
fixed_code = fixed_code.replace('connect_timeout=8', 'connect_timeout=CONNECTION_TIMEOUT_SEC')

# 7. Update docstring
fixed_code = fixed_code.replace(
    'NewPayloadUpdatedWizard_v132.py',
    'NewPayloadUpdatedWizard_v133_Fixed.py'
)

# Write the fixed file
with open('NewPayloadUpdated_FIXED.py', 'w', encoding='utf-8') as f:
    f.write(fixed_code)

# Now display the entire code
print(fixed_code)
