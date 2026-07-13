"""
Executor for running Python code in isolation.
Currently supports only Python. Other languages will be added later.
"""

import ast                # Abstract Syntax Tree – parse Python code without executing it
import subprocess         # Run external processes (shell commands)
import tempfile           # Create temporary directories and files
from pathlib import Path  # Cross-platform path handling
from typing import Tuple


class ExecutionResult:
    """
    Container for code execution result.
    Stores success flag, stdout, stderr, and return code.
    """
    def __init__(self, success: bool, output: str = "", error: str = "", returncode: int = -1):
        self.success = success          # True if code executed without errors
        self.output = output            # Captured stdout
        self.error = error              # Captured stderr or error message
        self.returncode = returncode    # Process return code (0 = success)

    def __repr__(self):
        return f"ExecutionResult(success={self.success}, returncode={self.returncode})"


def static_validate(code: str) -> ExecutionResult:
    """
    Static syntax check for Python without executing the code.
    Uses ast.parse() – it only checks syntax, does not run the code.
    Returns ExecutionResult: success=True if syntax is OK, else False with error description.
    """
    try:
        ast.parse(code)
        return ExecutionResult(True, output="Syntax OK")
    except SyntaxError as e:
        return ExecutionResult(False, error=f"SyntaxError: {e}")
    except Exception as e:
        return ExecutionResult(False, error=f"Static validation error: {e}")


def run_in_subprocess(code: str, timeout: int = 10) -> ExecutionResult:
    """
    Runs Python code in a temporary directory with a time limit.
    - Creates a temp folder (tempfile.TemporaryDirectory).
    - Writes code to script.py inside it.
    - Runs subprocess.run() with 'python script.py'.
    - Captures stdout, stderr, return code.
    - Folder is automatically deleted after the block (context manager).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "script.py"
        script_path.write_text(code, encoding="utf-8")

        try:
            result = subprocess.run(
                ["python", str(script_path)],
                capture_output=True,           # Capture stdout and stderr
                text=True,                     # Return as text strings (not bytes)
                timeout=timeout,               # Kill the process if it runs too long
                cwd=tmpdir,                    # Set working directory to temp folder
                env={"PYTHONPATH": ""}         # Isolate from system Python modules
            )

            if result.returncode == 0:
                return ExecutionResult(
                    success=True,
                    output=result.stdout,
                    error=result.stderr,
                    returncode=result.returncode
                )
            else:
                return ExecutionResult(
                    success=False,
                    output=result.stdout,
                    error=result.stderr or result.stdout,
                    returncode=result.returncode
                )

        except subprocess.TimeoutExpired:
            return ExecutionResult(False, error=f"Timeout after {timeout}s")
        except Exception as e:
            return ExecutionResult(False, error=f"Execution error: {e}")


def execute_code(code: str, allow_exec: bool = False, timeout: int = 10) -> ExecutionResult:
    """
    Main entry point for code execution.
    Always runs static validation.
    If allow_exec=True, runs the code in subprocess.
    If allow_exec=False, returns success without actual execution (only static check).
    """
    # 1. Static validation (always)
    static = static_validate(code)
    if not static.success:
        return static

    # 2. If execution is not allowed – return success without running
    if not allow_exec:
        return ExecutionResult(True, output="Static validation passed (execution disabled)")

    # 3. Real execution
    return run_in_subprocess(code, timeout)