"""Constraint Examples for Agent Steering.

This module provides concrete constraint functions that can be used
to steer AI coding agents during generation.

Each constraint is a predicate: code -> bool
- Returns True if code satisfies the constraint
- Returns False if code violates the constraint

During SMC steering, violated constraints cause particle rejection.
"""

import ast
import importlib
import re
import subprocess
from pathlib import Path

# ==============================================================================
# SYNTAX CONSTRAINTS
# ==============================================================================


def syntax_valid(code: str) -> bool:
    """Code must parse as valid Python.

    Effect: IMPOSSIBLE to generate syntactically invalid code.

    Example violation:
        def foo(
            return x  # SyntaxError: missing closing paren
    """
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def indentation_consistent(code: str) -> bool:
    """Indentation must be consistent (all spaces or all tabs).

    Effect: IMPOSSIBLE to mix tabs and spaces.
    """
    has_tabs = "\t" in code
    has_spaces = re.search(r"^ +", code, re.MULTILINE) is not None

    # Either all tabs, all spaces, or neither (no indentation)
    return not (has_tabs and has_spaces)


# ==============================================================================
# TYPE SAFETY CONSTRAINTS
# ==============================================================================


def type_checks(code: str, temp_file: str = "/tmp/check.py") -> bool:
    """Code must pass pyright type checking.

    Effect: IMPOSSIBLE to generate code with type errors.

    Example violation:
        def add(x: int, y: int) -> int:
            return str(x + y)  # Type error: returns str, not int
    """
    # Write code to temp file
    Path(temp_file).write_text(code)

    # Run pyright
    result = subprocess.run(
        ["pyright", temp_file, "--outputjson"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    # Check if there are errors
    try:
        import json

        output = json.loads(result.stdout)
        return output.get("summary", {}).get("errorCount", 1) == 0
    except (json.JSONDecodeError, KeyError):
        # If can't parse output, assume failure
        return False


def has_type_hints(code: str) -> bool:
    """All function signatures must have type hints.

    Effect: IMPOSSIBLE to generate functions without types.

    Example violation:
        def process(data):  # Missing type hints
            return data
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check parameters have annotations
            for arg in node.args.args:
                if arg.annotation is None:
                    return False

            # Check return type annotation
            if node.returns is None and node.name != "__init__":
                return False

    return True


# ==============================================================================
# SECURITY CONSTRAINTS
# ==============================================================================


def no_sql_injection(code: str) -> bool:
    """No string interpolation in SQL queries.

    Effect: IMPOSSIBLE to generate SQL injection vulnerabilities.

    Example violation:
        query = f"SELECT * FROM users WHERE id={user_id}"  # Unsafe!
    """
    # Pattern: f-string or .format() with SQL keywords
    sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE"]

    for keyword in sql_keywords:
        # f-string interpolation
        if re.search(rf'f".*{keyword}.*\{{', code, re.IGNORECASE):
            return False
        if re.search(rf"f'.*{keyword}.*\{{", code, re.IGNORECASE):
            return False

        # .format() interpolation
        if re.search(rf'"{keyword}.*".format\(', code, re.IGNORECASE):
            return False
        if re.search(rf"'{keyword}.*'.format\(", code, re.IGNORECASE):
            return False

        # % formatting
        if re.search(rf'"{keyword}.*" %', code, re.IGNORECASE):
            return False

    return True


def no_hardcoded_secrets(code: str) -> bool:
    """No hardcoded passwords, API keys, or tokens.

    Effect: IMPOSSIBLE to commit secrets to code.

    Example violation:
        API_KEY = "sk-1234567890abcdef"  # Hardcoded secret!
    """
    # Pattern: Common secret variable names with string values
    secret_patterns = [
        r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
        r'(?:api_key|apikey|token)\s*=\s*["\'][^"\']+["\']',
        r'(?:secret|private_key)\s*=\s*["\'][^"\']+["\']',
    ]

    return all(not re.search(pattern, code, re.IGNORECASE) for pattern in secret_patterns)


def uses_secure_random(code: str) -> bool:
    """Must use secrets module for security-sensitive randomness.

    Effect: IMPOSSIBLE to use insecure random for crypto.

    Example violation:
        import random
        token = random.randint(0, 1000000)  # Not cryptographically secure!
    """
    # If code uses random for security, it must be secrets module
    if "random" in code and any(keyword in code for keyword in ["token", "password", "key", "secret"]):
        return "import secrets" in code or "from secrets import" in code

    return True


# ==============================================================================
# API CONSTRAINTS
# ==============================================================================


def no_hallucinated_imports(code: str) -> bool:
    """All imported modules and functions must exist.

    Effect: IMPOSSIBLE to import non-existent modules.

    Example violation:
        from nonexistent_lib import magic_function  # Hallucinated!
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        # Check import statements
        if isinstance(node, ast.Import):
            for alias in node.names:
                try:
                    importlib.import_module(alias.name)
                except ImportError:
                    return False

        # Check from ... import statements
        elif isinstance(node, ast.ImportFrom) and node.module:
            try:
                mod = importlib.import_module(node.module)
                # Check that imported names exist
                for alias in node.names:
                    if alias.name != "*" and not hasattr(mod, alias.name):
                        return False
            except ImportError:
                return False

    return True


# ==============================================================================
# ERROR HANDLING CONSTRAINTS
# ==============================================================================


def has_error_handling(code: str) -> bool:
    """Functions that call external resources must have try/except.

    Effect: IMPOSSIBLE to call risky operations without error handling.

    Example violation:
        def fetch_data(url):
            return requests.get(url)  # No error handling!
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    # Risky operations that need error handling
    risky_calls = ["requests.", "open(", "db.", "execute(", "json.loads"]

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check if function contains risky calls
            func_code = ast.unparse(node)
            has_risky = any(call in func_code for call in risky_calls)

            if has_risky:
                # Check if there's a try/except in the function
                has_try_except = any(isinstance(n, ast.Try) for n in ast.walk(node))
                if not has_try_except:
                    return False

    return True


def validates_input(code: str) -> bool:
    """Function parameters must be validated.

    Effect: IMPOSSIBLE to use user input without validation.

    Example violation:
        def process(user_id):
            db.query(f"SELECT * FROM users WHERE id={user_id}")  # No validation!
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    # Check for validation patterns
    validation_keywords = ["if not", "isinstance", "validate", "check", "raise ValueError", "raise TypeError"]

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # If function has parameters, it should validate them
            if node.args.args:
                func_code = ast.unparse(node)
                # Check for validation keywords
                has_validation = any(kw in func_code for kw in validation_keywords)
                if not has_validation:
                    return False

    return True


# ==============================================================================
# ARCHITECTURAL CONSTRAINTS
# ==============================================================================


def follows_naming_convention(code: str) -> bool:
    """Functions and variables must use snake_case.

    Effect: IMPOSSIBLE to violate naming conventions.

    Example violation:
        def loginUser():  # Should be login_user
            userName = "test"  # Should be user_name
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        # Check function names
        if isinstance(node, ast.FunctionDef):
            if not re.match(r"^[a-z_][a-z0-9_]*$", node.name) and not node.name.startswith("__"):
                return False

        # Check variable names
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            name = node.id
            # Allow CONSTANTS in UPPER_CASE
            if name.isupper():
                continue
            # Otherwise must be snake_case
            if not re.match(r"^[a-z_][a-z0-9_]*$", name):
                return False

    return True


def has_docstrings(code: str) -> bool:
    """All functions must have docstrings.

    Effect: IMPOSSIBLE to generate undocumented functions.

    Example violation:
        def process(data):  # Missing docstring!
            return data
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check if first statement is a docstring
            if not node.body:
                return False

            first = node.body[0]
            if not isinstance(first, ast.Expr) or not isinstance(first.value, ast.Constant):
                return False

    return True


def max_function_length(code: str, max_lines: int = 50) -> bool:
    """Functions must not exceed maximum line count.

    Effect: IMPOSSIBLE to generate overly long functions.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Count lines in function body
            func_code = ast.unparse(node)
            line_count = len(func_code.split("\n"))
            if line_count > max_lines:
                return False

    return True


# ==============================================================================
# TESTING CONSTRAINTS
# ==============================================================================


def has_test_coverage(code: str, test_code: str | None = None) -> bool:
    """All public functions must have corresponding tests.

    Effect: IMPOSSIBLE to generate untested code.
    """
    if test_code is None:
        # No test code provided, check if this IS test code
        return "def test_" in code or "class Test" in code

    try:
        code_tree = ast.parse(code)
        test_tree = ast.parse(test_code)
    except SyntaxError:
        return False

    # Extract function names from code
    code_functions = {
        node.name for node in ast.walk(code_tree) if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }

    # Extract test function names
    test_functions = {
        node.name for node in ast.walk(test_tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }

    # Check each code function has a test
    for func_name in code_functions:
        test_name = f"test_{func_name}"
        if test_name not in test_functions:
            return False

    return True


# ==============================================================================
# COMPOSITE CONSTRAINTS
# ==============================================================================


def production_ready(code: str) -> bool:
    """Code must satisfy all production-readiness constraints.

    Combines multiple constraints for high-quality code.
    """
    return all(
        [
            syntax_valid(code),
            has_error_handling(code),
            validates_input(code),
            follows_naming_convention(code),
            has_docstrings(code),
        ]
    )


def security_hardened(code: str) -> bool:
    """Code must satisfy all security constraints.

    Combines multiple security-focused constraints.
    """
    return all(
        [
            no_sql_injection(code),
            no_hardcoded_secrets(code),
            uses_secure_random(code),
            has_error_handling(code),
            validates_input(code),
        ]
    )


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    # Example: Valid code
    valid_code = '''
def login_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user with username and password.

    Args:
        username: User's username
        password: User's password

    Returns:
        User dict if valid, None otherwise
    """
    if not isinstance(username, str) or not isinstance(password, str):
        raise TypeError("Username and password must be strings")

    try:
        query = "SELECT * FROM users WHERE username = ?"
        result = db.execute(query, (username,))
        user = result.fetchone()

        if user and verify_password(password, user["password_hash"]):
            return user
    except DatabaseError as e:
        logger.error(f"Database error during login: {e}")
        return None

    return None
'''

    # Example: Invalid code (SQL injection)
    invalid_code = """
def login(username, password):
    query = f"SELECT * FROM users WHERE username='{username}'"
    return db.execute(query)
"""

    print("Testing constraints on VALID code:")
    print(f"  syntax_valid: {syntax_valid(valid_code)}")
    print(f"  has_type_hints: {has_type_hints(valid_code)}")
    print(f"  no_sql_injection: {no_sql_injection(valid_code)}")
    print(f"  has_error_handling: {has_error_handling(valid_code)}")
    print(f"  validates_input: {validates_input(valid_code)}")
    print(f"  has_docstrings: {has_docstrings(valid_code)}")
    print()

    print("Testing constraints on INVALID code:")
    print(f"  syntax_valid: {syntax_valid(invalid_code)}")
    print(f"  has_type_hints: {has_type_hints(invalid_code)}")
    print(f"  no_sql_injection: {no_sql_injection(invalid_code)}")  # Should be False
    print(f"  has_error_handling: {has_error_handling(invalid_code)}")  # Should be False
    print(f"  validates_input: {validates_input(invalid_code)}")  # Should be False
    print(f"  has_docstrings: {has_docstrings(invalid_code)}")  # Should be False
