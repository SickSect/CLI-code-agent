"""Static validation of generated code, per language.

Syntax is checked WITHOUT running the program. Python uses the built-in `ast`
parser; other languages shell out to their own toolchain in a temp directory.
Adding a language means writing one validator and adding one registry entry.

Two different outcomes are reported separately:
  success=False                -> the code is broken; the fixer should act on it
  success=True, validated=False -> we could not check it (no toolchain, unknown
                                   language); the code is not blamed, but the
                                   caller must warn the user
"""

import ast
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from codeagent.exec_result import ExecutionResult

# Alternative spellings the planner may return -> canonical registry key.
_LANG_ALIASES = {
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "node": "javascript",
    "nodejs": "javascript",
    "ts": "typescript",
    "golang": "go",
    "c++": "cpp",
    "cxx": "cpp",
    "cc": "cpp",
    "c#": "csharp",
    "cs": "csharp",
    "dotnet": "csharp",
    "rb": "ruby",
    "rs": "rust",
    "kt": "kotlin",
    "kts": "kotlin",
    "sh": "bash",
    "shell": "bash",
}

# Seconds allowed for an external syntax checker before we give up on it.
# Compilers that boot a VM or a full backend (kotlinc, swiftc) need more.
_TOOL_TIMEOUT = 20
_SLOW_TOOL_TIMEOUT = 60


def _normalize_language(language: str) -> str:
    """Map a language name to its canonical key in _VALIDATORS."""
    if not language:
        return "python"
    key = language.strip().lower()
    return _LANG_ALIASES.get(key, key)


def _is_blank(code: str) -> bool:
    """True when the model returned nothing usable.

    Important: ast.parse("") succeeds, so an empty answer would otherwise pass
    validation and be reported as correct code.
    """
    return not code or not code.strip()


def _unchecked(reason: str) -> ExecutionResult:
    """Result for 'we could not check this', as opposed to 'this is broken'.

    success stays True so the code is not sent to the fixer over a missing
    toolchain; validated=False tells the caller to warn the user instead.
    """
    return ExecutionResult(True, validated=False, error=reason)


def _resolve_tool(candidates: list) -> str:
    """Return the first installed tool from the candidate list, or None."""
    for tool in candidates:
        if shutil.which(tool):
            return tool
    return None


def _run_syntax_tool(code: str, filename: str, tools: list, build_args,
                     timeout: int = _TOOL_TIMEOUT) -> ExecutionResult:
    """Write the code to a temp file and syntax-check it with an external tool.

    `tools` is a list of interchangeable executables, tried in order (e.g. gcc
    then clang). `build_args(tool, path, tmpdir)` returns the argv list to run.
    The tool must exit 0 on valid code and non-zero otherwise.
    """
    tool = _resolve_tool(tools)
    if tool is None:
        return _unchecked(
            f"Validation requires one of: {', '.join(tools)} — none is installed"
        )

    # ignore_cleanup_errors: on Windows the temp dir can still be locked by the
    # tool process when the context manager exits.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        path = Path(tmpdir) / filename
        path.write_text(code, encoding="utf-8")
        try:
            result = subprocess.run(
                build_args(tool, path, Path(tmpdir)),
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
            )
        except subprocess.TimeoutExpired:
            # The checker gave up, which says nothing about the code itself.
            return _unchecked(f"Validation timeout after {timeout}s")
        except Exception as e:
            return _unchecked(f"Validation could not run: {e}")

    if result.returncode == 0:
        return ExecutionResult(True, output="Syntax OK")

    message = (result.stderr or result.stdout).strip()
    # Temp paths leak into tool output and mean nothing to the fixer.
    message = message.replace(str(path), path.name).replace(str(path.parent), "")
    return ExecutionResult(False, error=f"SyntaxError: {message}")


# --------------------------------------------------------------------------
# Per-language validators
# --------------------------------------------------------------------------

def _find_stubs(tree: ast.AST) -> list:
    """Return names of Python functions whose body is only a placeholder.

    The coder prompt forbids stubs (`...`, bare `pass`, empty bodies), but the
    model does not always comply, and a stub passes a syntax check happily.
    """
    stubs = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = [
            stmt for stmt in node.body
            # Drop the docstring, if any: it is not an implementation.
            if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)
                    and isinstance(stmt.value.value, str))
        ]
        if not body:
            stubs.append(node.name)
            continue
        if len(body) == 1:
            only = body[0]
            is_pass = isinstance(only, ast.Pass)
            is_ellipsis = (isinstance(only, ast.Expr) and isinstance(only.value, ast.Constant)
                           and only.value.value is Ellipsis)
            if is_pass or is_ellipsis:
                stubs.append(node.name)
    return stubs


def _validate_python(code: str) -> ExecutionResult:
    """Parse Python with ast (no execution), then reject blanks and stubs."""
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ExecutionResult(False, error=f"SyntaxError: line {e.lineno}: {e.msg}")
    except Exception as e:
        return ExecutionResult(False, error=f"Static validation error: {e}")

    stubs = _find_stubs(tree)
    if stubs:
        return ExecutionResult(
            False,
            error=f"Unimplemented function(s): {', '.join(stubs)} — body is a stub",
        )
    return ExecutionResult(True, output="Syntax OK")


def _validate_javascript(code: str) -> ExecutionResult:
    """Syntax-check JavaScript with `node --check` (parses, does not run)."""
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(code, "check.js", ["node"],
                            lambda tool, p, d: [tool, "--check", str(p)])


def _validate_typescript(code: str) -> ExecutionResult:
    """Type-check TypeScript with `tsc --noEmit` (writes nothing to disk)."""
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(code, "check.ts", ["tsc"],
                            lambda tool, p, d: [tool, "--noEmit", "--skipLibCheck", str(p)])


def _validate_go(code: str) -> ExecutionResult:
    """Parse Go with `gofmt -e`.

    gofmt only parses, so it needs no module or package setup — unlike `go vet`,
    which expects a real package on disk.
    """
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(code, "check.go", ["gofmt"],
                            lambda tool, p, d: [tool, "-e", "-l", str(p)])


def _validate_c(code: str) -> ExecutionResult:
    """Check C with `-fsyntax-only`: the compiler parses but emits no object."""
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(code, "check.c", ["gcc", "clang", "cc"],
                            lambda tool, p, d: [tool, "-fsyntax-only", str(p)])


def _validate_cpp(code: str) -> ExecutionResult:
    """Check C++ with `-fsyntax-only`: parsing and semantics, no build output."""
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(code, "check.cpp", ["g++", "clang++", "c++"],
                            lambda tool, p, d: [tool, "-fsyntax-only", "-std=c++17", str(p)])


def _java_filename(code: str) -> str:
    """Derive the file name javac expects from the public type in the code.

    javac requires the file to be named after its public class/interface/enum/
    record, so a fixed "check.java" would fail on otherwise valid code.
    """
    match = re.search(
        r"public\s+(?:final\s+|abstract\s+|sealed\s+|static\s+)*"
        r"(?:class|interface|enum|record)\s+(\w+)",
        code,
    )
    if not match:
        # No public type: any name works, but keep it consistent with a
        # package-private class if we can find one.
        match = re.search(r"(?:class|interface|enum|record)\s+(\w+)", code)
    return f"{match.group(1)}.java" if match else "Check.java"


def _validate_java(code: str) -> ExecutionResult:
    """Compile Java with javac into a temp dir (checks syntax and symbols)."""
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(code, _java_filename(code), ["javac"],
                            lambda tool, p, d: [tool, "-d", str(d), str(p)])


def _validate_csharp(code: str) -> ExecutionResult:
    """Compile C# to a throwaway library with the Roslyn (csc) or Mono (mcs) compiler."""
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(
        code, "Check.cs", ["csc", "mcs"],
        lambda tool, p, d: [tool, "-nologo", "-target:library",
                            f"-out:{d / 'check.dll'}", str(p)],
    )


def _validate_ruby(code: str) -> ExecutionResult:
    """Syntax-check Ruby with `ruby -c` (parses only, runs nothing)."""
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(code, "check.rb", ["ruby"],
                            lambda tool, p, d: [tool, "-c", str(p)])


def _validate_php(code: str) -> ExecutionResult:
    """Syntax-check PHP with `php -l` (lint mode, no execution)."""
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(code, "check.php", ["php"],
                            lambda tool, p, d: [tool, "-l", str(p)])


def _validate_rust(code: str) -> ExecutionResult:
    """Check Rust with `rustc --emit=metadata`: full type check, no binary.

    Built as a library crate so the code does not need a `main` function.
    """
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(
        code, "check.rs", ["rustc"],
        lambda tool, p, d: [tool, "--edition=2021", "--crate-type=lib",
                            "--emit=metadata", "-o", str(d / "check.rmeta"), str(p)],
    )


def _validate_kotlin(code: str) -> ExecutionResult:
    """Compile Kotlin with kotlinc into a temp dir (syntax and types)."""
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(
        code, "check.kt", ["kotlinc"],
        lambda tool, p, d: [tool, str(p), "-nowarn", "-d", str(d)],
        timeout=_SLOW_TOOL_TIMEOUT,   # kotlinc starts a JVM on every run
    )


def _validate_swift(code: str) -> ExecutionResult:
    """Check Swift with `swiftc -typecheck`: parses and type-checks, emits nothing."""
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(code, "check.swift", ["swiftc"],
                            lambda tool, p, d: [tool, "-typecheck", str(p)],
                            timeout=_SLOW_TOOL_TIMEOUT)


def _validate_bash(code: str) -> ExecutionResult:
    """Syntax-check a shell script with `bash -n` (reads it, never runs it)."""
    if _is_blank(code):
        return ExecutionResult(False, error="Empty code")
    return _run_syntax_tool(code, "check.sh", ["bash", "sh"],
                            lambda tool, p, d: [tool, "-n", str(p)])


# language -> validator. Add a language by adding one line here.
_VALIDATORS = {
    "python": _validate_python,
    "javascript": _validate_javascript,
    "typescript": _validate_typescript,
    "go": _validate_go,
    "c": _validate_c,
    "cpp": _validate_cpp,
    "java": _validate_java,
    "csharp": _validate_csharp,
    "ruby": _validate_ruby,
    "php": _validate_php,
    "rust": _validate_rust,
    "kotlin": _validate_kotlin,
    "swift": _validate_swift,
    "bash": _validate_bash,
}


def definite_static_validate(code: str, language: str = "python") -> ExecutionResult:
    """Validate code for the given language without running it.

    An unknown language is reported as unchecked (validated=False), not as
    broken code: nothing is wrong with the code, we simply have no checker.
    """
    lang = _normalize_language(language)
    validator = _VALIDATORS.get(lang)
    if validator is None:
        supported = ", ".join(sorted(_VALIDATORS))
        return _unchecked(
            f"No static validator for '{language}' — code left unvalidated "
            f"(supported: {supported})"
        )
    return validator(code)