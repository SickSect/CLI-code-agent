"""
Executor for running Python code in isolation.
Currently supports only Python. Other languages will be added later.
"""

import os  # Access the current environment for the sandbox
import subprocess  # Run external processes (shell commands)
import sys  # sys.executable -> the Python running this process
import tempfile  # Create temporary directories and files
from pathlib import Path  # Cross-platform path handling

from codeagent.exec_result import ExecutionResult
from codeagent.static_code_validation import definite_static_validate

# Resource limits below rely on POSIX-only APIs (resource, preexec_fn, setsid).
# On Windows they are unavailable, so only the timeout applies there — use the
# Docker backend for real isolation on non-POSIX platforms.
_IS_POSIX = os.name == "posix"


def _resource_limits(mem_mb: int, cpu_secs: int):
    """Build a preexec_fn that caps the child's resources (POSIX only).

    The returned callable runs inside the child process after fork and before
    exec, applying hard limits on memory, CPU time and file size. Returns None
    on non-POSIX platforms, where such limits cannot be set this way.
    """
    if not _IS_POSIX:
        return None

    import resource  # imported lazily: the module does not exist on Windows

    def _apply() -> None:
        mem_bytes = mem_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))  # max RAM
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_secs, cpu_secs))  # max CPU seconds
        resource.setrlimit(resource.RLIMIT_FSIZE, (5_000_000, 5_000_000))  # max file size

    return _apply

def strip_code_fences(text: str) -> str:
    """Extract runnable code from a model response, dropping markdown fences.

    Local models frequently wrap code in ```python ... ``` blocks even when
    told not to. If a fenced block is present, return its contents (first block
    only); otherwise return the text stripped of surrounding whitespace.
    """
    lines = text.splitlines()
    if not any(line.lstrip().startswith("```") for line in lines):
        return text.strip()

    captured: list[str] = []
    inside = False
    for line in lines:
        if line.lstrip().startswith("```"):
            if not inside:
                inside = True  # opening fence -> start capturing
                continue
            break  # closing fence -> stop at first block
        if inside:
            captured.append(line)
    return "\n".join(captured).strip() if captured else text.strip()

def run_in_docker(code: str,
                  v: str = ":/app:ro",
                  network: str = "none",
                  memory: str = "256m",
                  pids_limit: int = 32,
                  image: str = "python:3.12-slim",
                  script_name: str = "script.py",
                  timeout: int = 10,
                  ):
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / script_name
        script_path.write_text(code, encoding="utf-8")

        args = []
        args.append('docker')
        args.append('run')
        args.append('--rm')
        args.append('-v')
        args.append(f"{tmpdir}{v}")
        args.append('--network')
        args.append(network)
        args.append('--memory')
        args.append(memory)
        args.append('--pids-limit')
        args.append(str(pids_limit))
        args.append(image)
        args.append("python")
        args.append(f"/app/{script_name}")

        run_kwargs = dict(
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        try:
            result = subprocess.run(
                args,  # -I = isolated mode
                **run_kwargs,
            )

            if result.returncode == 0:
                return ExecutionResult(
                    success=True,
                    output=result.stdout,
                    error=result.stderr,
                    returncode=result.returncode,
                )
            return ExecutionResult(
                success=False,
                output=result.stdout,
                error=result.stderr or result.stdout,
                returncode=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(False, error=f"Timeout after {timeout}s")
        except Exception as e:
            return ExecutionResult(False, error=f"Execution error: {e}")


def run_in_subprocess(
        code: str,
        timeout: int = 10,
        mem_mb: int = 256,
        cpu_secs: int = 5,
) -> ExecutionResult:
    """Run Python code in a throwaway directory with limits and a timeout.

    On POSIX, memory / CPU / file-size limits are applied so a runaway snippet
    cannot exhaust the machine (see _resource_limits). These are unavailable on
    Windows, where only the timeout applies. Steps:
    - create a temp folder (auto-deleted on exit),
    - write the code to script.py,
    - run it with `python -I` (isolated mode) in its own process group,
    - capture stdout, stderr and the return code.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "script.py"
        script_path.write_text(code, encoding="utf-8")

        run_kwargs = dict(
            capture_output=True,  # Capture stdout and stderr
            text=True,  # Return text, not bytes
            timeout=timeout,  # Kill if it runs too long
            cwd=tmpdir,  # Work inside the temp folder
            env={**os.environ, "PYTHONPATH": ""},  # keep PATH, drop PYTHONPATH
        )

        preexec = _resource_limits(mem_mb, cpu_secs)
        if preexec is not None:  # POSIX only
            run_kwargs["preexec_fn"] = preexec
            run_kwargs["start_new_session"] = True  # own group -> kill children too

        try:
            result = subprocess.run(
                [sys.executable, "-I", str(script_path)],  # -I = isolated mode
                **run_kwargs,
            )

            if result.returncode == 0:
                return ExecutionResult(
                    success=True,
                    output=result.stdout,
                    error=result.stderr,
                    returncode=result.returncode,
                )
            return ExecutionResult(
                success=False,
                output=result.stdout,
                error=result.stderr or result.stdout,
                returncode=result.returncode,
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(False, error=f"Timeout after {timeout}s")
        except Exception as e:
            return ExecutionResult(False, error=f"Execution error: {e}")

def _docker_available(timeout) -> bool:
    run_kwargs = dict(
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    try:
        docker_contains = subprocess.run(
            ['docker', '--version'],  # -I = isolated mode
            **run_kwargs,
        )
        if docker_contains.stdout.__contains__('Docker version'):
            return True
    except Exception as e:
        return False
    return False

def execute_code(code: str,
                 allow_exec: bool = False,
                 timeout: int = 10,
                 backend: str = "subprocess",
                 language: str = "python") -> ExecutionResult:
    """
    Main entry point for code execution.
    Always runs static validation.
    If allow_exec=True, runs the code in subprocess.
    If allow_exec=False, returns success without actual execution (only static check).
    """
    # 1. Static validation (always)
    static = definite_static_validate(code, language)
    if not static.success:
        return static
    if not allow_exec:
        return static

    if backend == 'docker':
        if _docker_available(timeout):
            return run_in_docker(code)
        else:
            return static
    elif backend == 'subprocess' and allow_exec:
        result = run_in_subprocess(code)
        return result
    return static
