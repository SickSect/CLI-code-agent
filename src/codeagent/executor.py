"""Execution of generated code, per language, in isolation.

Every language is described once in languages.yaml: which local executables can
run it, which Docker image contains them, and which command steps turn a source
file into a running program. Compiled languages need two steps (build, then
run); the temp directory is shared between them, so one description works both
locally and inside a container.

Resolution order for every run: local toolchain first, Docker image second, and
an honest failure if neither is available.
"""

import os  # Access the current environment for the sandbox
import shutil  # Locate executables on PATH
import subprocess  # Run external processes
import sys  # Platform checks
import tempfile  # Create temporary directories and files
from pathlib import Path  # Cross-platform path handling

import yaml  # Read languages.yaml

from codeagent.exec_result import ExecutionResult
from codeagent.static_code_validation import _normalize_language, definite_static_validate

# Resource limits below rely on POSIX-only APIs (resource, preexec_fn, setsid).
# On Windows they are unavailable, so only the timeout applies there — use the
# Docker backend for real isolation on non-POSIX platforms.
_IS_POSIX = os.name == "posix"

# Name of the compiled artifact for languages that build before running.
_BINARY = "app.exe" if sys.platform == "win32" else "app"

_DOCKER_TIMEOUT_EXTRA = 300  # first run of a language may pull its image

_docker_ready = None  # cached result of the daemon check

# --------------------------------------------------------------------------
# Language table, loaded once at import
# --------------------------------------------------------------------------
# Path is taken relative to this module, so it resolves no matter which
# directory the CLI was started from.
_CONFIG_PATH = Path(__file__).parent / "languages.yaml"
with open(_CONFIG_PATH, encoding="utf-8") as config_file:
    _CONFIG = yaml.safe_load(config_file)

_RUN_SPECS = _CONFIG["languages"]
# Runtimes that reserve a huge virtual address space at startup (V8, JVM, Go's
# allocator, .NET). An RLIMIT_AS cap kills them before they run a line, so the
# address-space limit is skipped for these; CPU time and file size limits still
# apply, and Docker provides the real memory cap.
_VM_LANGUAGES = set(_CONFIG["vm_languages"])

# Extension used when a bare snippet has to be written to disk before running.
_SNIPPET_SUFFIXES = {
    "python": ".py",
    "javascript": ".js",
    "ruby": ".rb",
    "php": ".php",
    "bash": ".sh",
    "go": ".go",
    "c": ".c",
    "cpp": ".cpp",
    "rust": ".rs",
    "java": ".java",
    "csharp": ".cs",
    "swift": ".swift",
}


def supported_run_languages() -> list:
    """Languages this executor knows how to run."""
    return sorted(_RUN_SPECS)


def _build_steps(spec: dict, tool: str, entry: str, binary: str) -> list:
    """Turn the {placeholder} templates from languages.yaml into argv lists.

    Substitutes {tool}, {entry}, {binary} and {stem} (the entry file without its
    extension, which Java needs as the class name).
    """
    stem = Path(entry).stem
    return [
        [part.format(tool=tool, entry=entry, binary=binary, stem=stem) for part in step]
        for step in spec["steps"]
    ]


def _resource_limits(mem_mb: int, cpu_secs: int, cap_memory: bool = True):
    """Build a preexec_fn that caps the child's resources (POSIX only).

    The returned callable runs inside the child process after fork and before
    exec. Returns None on non-POSIX platforms, where such limits cannot be set
    this way.
    """
    if not _IS_POSIX:
        return None

    import resource  # imported lazily: the module does not exist on Windows

    def _apply() -> None:
        if cap_memory:
            mem_bytes = mem_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))  # max RAM
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_secs, cpu_secs))  # max CPU seconds
        resource.setrlimit(resource.RLIMIT_FSIZE, (50_000_000, 50_000_000))  # max file size

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

    captured: list = []
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


def _resolve_tool(candidates: list) -> str:
    """Return the first usable local executable, or None.

    On Windows, System32\\bash.exe is a WSL launcher rather than a shell: it is
    found by which() even when WSL is not set up, so it is not accepted here.
    """
    for tool in candidates:
        path = shutil.which(tool)
        if not path:
            continue
        if sys.platform == "win32":
            # System32\\bash.exe is a WSL launcher, not a shell.
            if tool in ("bash", "sh") and "system32" in path.replace("/", "\\").lower():
                continue
            # Microsoft Store "app execution aliases" are zero-byte stubs that
            # which() happily reports; running one fails with WinError 3.
            try:
                if os.path.getsize(path) == 0:
                    continue
            except OSError:
                continue
        return tool
    return None


def _docker_available(timeout: int = 15) -> bool:
    """True when the Docker daemon answers. Cached: the check is not free."""
    global _docker_ready
    if _docker_ready is not None:
        return _docker_ready
    if shutil.which("docker") is None:
        _docker_ready = False
        return False
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=timeout
        )
        _docker_ready = result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        _docker_ready = False
    return _docker_ready


def _write_files(files_content: dict, tmpdir: str) -> None:
    """Lay every generated file out in one directory so imports resolve."""
    for path, content in files_content.items():
        file_path = Path(tmpdir) / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")


def _as_result(result, step_index: int, total_steps: int) -> ExecutionResult:
    """Turn a finished subprocess into an ExecutionResult.

    A non-zero exit from a build step is a compile error, not a program failure,
    so the message says which stage broke.
    """
    if result.returncode == 0:
        return ExecutionResult(True, output=result.stdout, error=result.stderr, returncode=0)
    stage = "Build failed" if step_index < total_steps - 1 else "Execution failed"
    return ExecutionResult(
        success=False,
        output=result.stdout,
        error=f"{stage}: {result.stderr or result.stdout}",
        returncode=result.returncode,
    )


def _run_steps_locally(steps: list, tmpdir: str, timeout: int,
                       mem_mb: int, cpu_secs: int,
                       cap_memory: bool = True) -> ExecutionResult:
    """Run build/execute steps in order, stopping at the first failure."""
    run_kwargs = dict(
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=tmpdir,                            # relative paths resolve here
        env={**os.environ, "PYTHONPATH": ""},  # keep PATH, drop PYTHONPATH
    )
    preexec = _resource_limits(mem_mb, cpu_secs, cap_memory)
    if preexec is not None:  # POSIX only
        run_kwargs["preexec_fn"] = preexec
        run_kwargs["start_new_session"] = True  # own group -> kill children too

    last = None
    for index, argv in enumerate(steps):
        try:
            last = subprocess.run(argv, **run_kwargs)
        except subprocess.TimeoutExpired:
            return ExecutionResult(False, error=f"Timeout after {timeout}s")
        except Exception as e:
            return ExecutionResult(False, error=f"Execution error: {e}")
        if last.returncode != 0:
            return _as_result(last, index, len(steps))
    return _as_result(last, len(steps) - 1, len(steps))


def _run_steps_in_docker(steps: list, tmpdir: str, image: str,
                         timeout: int, memory: str, pids_limit: int) -> ExecutionResult:
    """Run the same steps inside a container, one `docker run` per step.

    The temp directory is mounted writable at /app, so a binary produced by the
    build step is still there for the run step.
    """
    base = [
        "docker", "run", "--rm",
        "--network", "none",                        # no network for generated code
        "-v", f"{Path(tmpdir).as_posix()}:/app",    # writable: builds emit output
        "-w", "/app",                               # same relative paths as locally
        "--memory", memory,
        "--pids-limit", str(pids_limit),
        image,
    ]
    last = None
    for index, argv in enumerate(steps):
        try:
            last = subprocess.run(
                base + argv,
                capture_output=True,
                text=True,
                timeout=timeout + _DOCKER_TIMEOUT_EXTRA,   # image pull on first run
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(False, error=f"Timeout after {timeout}s")
        except Exception as e:
            return ExecutionResult(False, error=f"Execution error: {e}")
        if last.returncode != 0:
            return _as_result(last, index, len(steps))
    return _as_result(last, len(steps) - 1, len(steps))


def run_files(files_content: dict,
              entry: str,
              language: str = "python",
              timeout: int = 10,
              backend: str = "subprocess",
              memory: str = "256m",
              pids_limit: int = 32,
              mem_mb: int = 256,
              cpu_secs: int = 5) -> ExecutionResult:
    """Write the generated files to a temp dir and run the entry point.

    Picks the toolchain for `language`: locally when installed, otherwise in the
    language's Docker image. `backend="docker"` skips the local toolchain and
    goes straight to the container.
    """
    lang = _normalize_language(language)
    spec = _RUN_SPECS.get(lang)
    if spec is None:
        return ExecutionResult(
            False,
            error=f"Cannot run '{language}' yet "
                  f"(supported: {', '.join(supported_run_languages())})",
        )

    image = spec["image"]
    tools = spec["tools"]
    # Executable name inside the image, when it differs from the first local
    # candidate (locally we may find clang, the image ships gcc).
    docker_tool = spec.get("docker_tool", tools[0])

    local_tool = None if backend == "docker" else _resolve_tool(tools)
    if local_tool is not None and lang == "python":
        # sys.executable is the interpreter running this process: it always
        # exists, unlike a "python3" found on PATH (which on Windows may be a
        # Microsoft Store stub).
        local_tool = sys.executable
    use_docker = local_tool is None
    if use_docker and not _docker_available():
        if backend == "docker":
            return ExecutionResult(
                False, error="Docker backend requested but Docker is not available"
            )
        return ExecutionResult(
            False,
            error=f"Cannot run {lang}: none of {', '.join(tools)} is installed "
                  f"and Docker is unavailable",
        )

    # ignore_cleanup_errors: on Windows the temp dir may still be locked by the
    # process that just exited.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        _write_files(files_content, tmpdir)

        if use_docker:
            # /app is where the temp dir is mounted inside the container.
            steps = _build_steps(spec, docker_tool, entry, f"/app/{_BINARY}")
            return _run_steps_in_docker(steps, tmpdir, image, timeout, memory, pids_limit)

        binary = str(Path(tmpdir) / _BINARY)
        steps = _build_steps(spec, local_tool, entry, binary)
        return _run_steps_locally(steps, tmpdir, timeout, mem_mb, cpu_secs,
                                  cap_memory=lang not in _VM_LANGUAGES)


def execute_code(code: str,
                 allow_exec: bool = False,
                 timeout: int = 10,
                 backend: str = "subprocess",
                 language: str = "python",
                 files_content: dict = None,
                 entry: str = None) -> ExecutionResult:
    """Validate generated code and, when allowed, run it.

    Always validates first: every file when a file set is given, otherwise the
    single snippet. Execution only happens with allow_exec=True.
    """
    # 1. Static validation (always). Two different outcomes:
    #    not success   -> the code is broken; report it so the fixer can act on it
    #    not validated -> we could not check it (no toolchain / unknown language);
    #                     the code is not blamed, but it is not run either
    if files_content:
        for path, content in files_content.items():
            result = definite_static_validate(content, language)
            if not result.success:
                return ExecutionResult(False, error=f"{path}: {result.error}")
            if not result.validated:
                return result
    else:
        static = definite_static_validate(code, language)
        if not static.success:
            return static
        if not static.validated:
            return static

    # 2. Execution gate
    if not allow_exec:
        return ExecutionResult(True, output="Static validation passed (execution disabled)")

    # 3. Run. A single snippet is just a one-file set.
    if not files_content:
        suffix = _SNIPPET_SUFFIXES.get(_normalize_language(language), ".txt")
        entry = entry or f"main{suffix}"
        files_content = {entry: code}

    return run_files(files_content, entry, language=language,
                     timeout=timeout, backend=backend)