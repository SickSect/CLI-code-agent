"""Tests for static_code_validation: one valid + one broken sample per language.

Languages whose toolchain is not installed are skipped, so the suite stays green
on any machine. Python and the dispatcher itself need no external tools and
always run.
"""

import shutil

import pytest

from codeagent.static_code_validation import (
    _VALIDATORS,
    _java_filename,
    _normalize_language,
    definite_static_validate,
)

# language -> (tools it can use, valid sample, broken sample)
LANGUAGE_SAMPLES = {
    "javascript": (
        ["node"],
        "function add(a, b) { return a + b; }",
        "function add(a, b) { return a + ; }",
    ),
    "typescript": (
        ["tsc"],
        "function add(a: number, b: number): number { return a + b; }",
        "function add(a: number, b: number): number { return a + ; }",
    ),
    "go": (
        ["gofmt"],
        "package main\n\nfunc add(a, b int) int { return a + b }\n",
        "package main\n\nfunc add(a, b int) int { return a + }\n",
    ),
    "c": (
        ["gcc", "clang", "cc"],
        "int add(int a, int b) { return a + b; }\n",
        "int add(int a, int b) { return a + b\n",
    ),
    "cpp": (
        ["g++", "clang++", "c++"],
        "#include <vector>\nint size() { std::vector<int> v; return v.size(); }\n",
        "#include <vector>\nint size() { std::vector<int> v return 1; }\n",
    ),
    "java": (
        ["javac"],
        "public class Calc { public int add(int a, int b) { return a + b; } }\n",
        "public class Calc { public int add(int a, int b) { return a + b } }\n",
    ),
    "csharp": (
        ["csc", "mcs"],
        "public class Calc { public int Add(int a, int b) { return a + b; } }\n",
        "public class Calc { public int Add(int a, int b) { return a + b } }\n",
    ),
    "ruby": (
        ["ruby"],
        "def add(a, b)\n  a + b\nend\n",
        "def add(a, b)\n  a + b\n",
    ),
    "php": (
        ["php"],
        "<?php\nfunction add($a, $b) { return $a + $b; }\n",
        "<?php\nfunction add($a, $b) { return $a + ; }\n",
    ),
    "rust": (
        ["rustc"],
        "pub fn add(a: i32, b: i32) -> i32 { a + b }\n",
        "pub fn add(a: i32, b: i32) -> i32 { a + }\n",
    ),
    "kotlin": (
        ["kotlinc"],
        "fun add(a: Int, b: Int): Int = a + b\n",
        "fun add(a: Int, b: Int): Int = a +\n",
    ),
    "swift": (
        ["swiftc"],
        "func add(a: Int, b: Int) -> Int { return a + b }\n",
        "func add(a: Int, b: Int) -> Int { return a + }\n",
    ),
    "bash": (
        ["bash", "sh"],
        "for i in 1 2 3; do\n  echo $i\ndone\n",
        "for i in 1 2 3; do\n  echo $i\n",
    ),
}


def _skip_if_missing(tools):
    if not any(shutil.which(t) for t in tools):
        pytest.skip(f"none of {tools} installed")


@pytest.mark.parametrize("language", sorted(LANGUAGE_SAMPLES))
def test_valid_code_passes(language):
    tools, valid, _ = LANGUAGE_SAMPLES[language]
    _skip_if_missing(tools)
    result = definite_static_validate(valid, language)
    assert result.success, f"{language}: valid code rejected: {result.error}"


@pytest.mark.parametrize("language", sorted(LANGUAGE_SAMPLES))
def test_broken_code_fails(language):
    tools, _, broken = LANGUAGE_SAMPLES[language]
    _skip_if_missing(tools)
    result = definite_static_validate(broken, language)
    assert not result.success, f"{language}: broken code accepted"
    assert result.error, f"{language}: failure reported without a message"


@pytest.mark.parametrize("language", sorted(LANGUAGE_SAMPLES))
def test_missing_toolchain_is_reported(language):
    """When a toolchain is absent, the error must say so instead of passing."""
    tools, valid, _ = LANGUAGE_SAMPLES[language]
    if any(shutil.which(t) for t in tools):
        pytest.skip("toolchain present, nothing to report")
    result = definite_static_validate(valid, language)
    assert not result.success
    assert "Validation requires" in result.error


# --- Python: no external tool, always runs -------------------------------

def test_python_valid():
    assert definite_static_validate("def add(a, b):\n    return a + b", "python").success


def test_python_syntax_error_reports_line():
    result = definite_static_validate("def add(:", "python")
    assert not result.success
    assert "line 1" in result.error


@pytest.mark.parametrize("code", [
    "def f():\n    ...",
    "def f():\n    pass",
    'def f():\n    """doc"""\n    pass',
])
def test_python_stub_is_rejected(code):
    result = definite_static_validate(code, "python")
    assert not result.success
    assert "stub" in result.error


@pytest.mark.parametrize("code", ["", "   ", "\n\n  \t"])
def test_blank_code_is_rejected(code):
    """ast.parse('') succeeds, so blanks must be caught explicitly."""
    result = definite_static_validate(code, "python")
    assert not result.success
    assert "Empty" in result.error


# --- Dispatcher and aliases ----------------------------------------------

@pytest.mark.parametrize("alias,canonical", [
    ("py", "python"), ("PY", "python"), ("Python3", "python"),
    ("js", "javascript"), ("node", "javascript"), ("NodeJS", "javascript"),
    ("c++", "cpp"), ("C#", "csharp"), ("golang", "go"),
    ("rb", "ruby"), ("rs", "rust"), ("kt", "kotlin"), ("sh", "bash"),
])
def test_alias_resolves(alias, canonical):
    assert _normalize_language(alias) == canonical
    assert canonical in _VALIDATORS


def test_unsupported_language_is_rejected():
    result = definite_static_validate("PROCEDURE DIVISION.", "cobol")
    assert not result.success
    assert "cobol" in result.error
    assert "supported:" in result.error


def test_unsupported_language_lists_registry():
    result = definite_static_validate("x", "brainfuck")
    for language in _VALIDATORS:
        assert language in result.error


@pytest.mark.parametrize("code,expected", [
    ("public class Calculator { }", "Calculator.java"),
    ("public final class Repo { }", "Repo.java"),
    ("public interface Store { }", "Store.java"),
    ("class Helper { }", "Helper.java"),
    ("// no type at all", "Check.java"),
])
def test_java_filename_follows_public_type(code, expected):
    """javac demands the file be named after its public type."""
    assert _java_filename(code) == expected