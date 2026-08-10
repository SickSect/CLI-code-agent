"""Tests for the executor: language table, multi-file layout, and the
success / validated distinction.

Languages whose toolchain is missing are skipped, so the suite is green on any
machine. Python always runs, since it is the interpreter running the tests.
"""

import shutil

import pytest

from codeagent.executor import (
    _RUN_SPECS,
    _VM_LANGUAGES,
    _build_steps,
    execute_code,
    run_files,
    supported_run_languages,
)

# language -> (local tools, entry file, source, expected stdout fragment)
RUN_SAMPLES = {
    "python": (["python3", "python"], "main.py",
               "print('py works')", "py works"),
    "javascript": (["node"], "main.js",
                   "console.log('js works')", "js works"),
    "bash": (["bash", "sh"], "main.sh",
             "echo bash works", "bash works"),
    "ruby": (["ruby"], "main.rb",
             "puts 'ruby works'", "ruby works"),
    "php": (["php"], "main.php",
            "<?php echo 'php works';", "php works"),
    "go": (["go"], "main.go",
           'package main\nimport "fmt"\nfunc main(){fmt.Println("go works")}\n', "go works"),
    "c": (["gcc", "clang", "cc"], "main.c",
          '#include <stdio.h>\nint main(){printf("c works\\n");return 0;}', "c works"),
    "cpp": (["g++", "clang++", "c++"], "main.cpp",
            '#include <iostream>\nint main(){std::cout<<"cpp works\\n";return 0;}', "cpp works"),
    "rust": (["rustc"], "main.rs",
             'fn main(){println!("rust works");}', "rust works"),
    "java": (["javac"], "Main.java",
             'public class Main{public static void main(String[] a){System.out.println("java works");}}',
             "java works"),
}


def _skip_if_missing(tools):
    if not any(shutil.which(t) for t in tools):
        pytest.skip(f"none of {tools} installed")


# --- the language table ---------------------------------------------------

def test_every_spec_has_required_keys():
    """A malformed languages.yaml entry must not fail later, at run time."""
    for language, spec in _RUN_SPECS.items():
        assert "image" in spec, f"{language}: no image"
        assert spec.get("tools"), f"{language}: no tools"
        assert spec.get("steps"), f"{language}: no steps"
        for step in spec["steps"]:
            assert isinstance(step, list) and step, f"{language}: bad step {step}"


def test_vm_languages_are_known():
    """vm_languages must reference languages that actually exist."""
    for language in _VM_LANGUAGES:
        # kotlin is validated but not runnable yet; ignore it here.
        if language == "kotlin":
            continue
        assert language in _RUN_SPECS, f"{language} listed in vm_languages but not runnable"


def test_build_steps_substitutes_placeholders():
    steps = _build_steps(_RUN_SPECS["python"], "python3", "main.py", "/tmp/app")
    assert steps == [["python3", "main.py"]]


def test_build_steps_two_stage_for_compiled():
    """C needs build then run, with the binary path shared between the steps."""
    steps = _build_steps(_RUN_SPECS["c"], "gcc", "main.c", "/tmp/app")
    assert len(steps) == 2
    assert "/tmp/app" in steps[0]      # build writes it
    assert steps[1] == ["/tmp/app"]    # run executes it


def test_build_steps_stem_for_java():
    """java runs the class named after the file, not the file itself."""
    steps = _build_steps(_RUN_SPECS["java"], "javac", "Calc.java", "/tmp/app")
    assert steps[-1][-1] == "Calc"


# --- running code ---------------------------------------------------------

@pytest.mark.parametrize("language", sorted(RUN_SAMPLES))
def test_language_runs_and_prints(language):
    tools, entry, source, expected = RUN_SAMPLES[language]
    _skip_if_missing(tools)
    result = run_files({entry: source}, entry, language=language)
    assert result.success, f"{language} failed: {result.error}"
    assert expected in result.output


def test_multi_file_imports_resolve():
    """All files land in one directory, so plain imports between them work."""
    files = {
        "models.py": "class User:\n    def __init__(self, name): self.name = name",
        "repository.py": "from models import User\n"
                         "class Repo:\n"
                         "    def __init__(self): self.items = []\n"
                         "    def add(self, u): self.items.append(u)\n"
                         "    def names(self): return [u.name for u in self.items]",
        "main.py": "from models import User\n"
                   "from repository import Repo\n"
                   "r = Repo()\n"
                   "r.add(User('Alice'))\n"
                   "print(r.names())",
    }
    result = run_files(files, "main.py", language="python")
    assert result.success, result.error
    assert "Alice" in result.output


def test_runtime_error_is_reported():
    result = run_files({"main.py": "raise ValueError('boom')"}, "main.py", language="python")
    assert not result.success
    assert "ValueError" in result.error
    assert result.returncode != 0


def test_timeout_is_enforced():
    result = run_files({"main.py": "while True: pass"}, "main.py",
                       language="python", timeout=2)
    assert not result.success
    assert "Timeout" in result.error


def test_build_failure_is_labelled_as_build():
    """A compile error must not look like a program crash."""
    _skip_if_missing(["gcc", "clang", "cc"])
    result = run_files({"main.c": "int main(){ return }"}, "main.c", language="c")
    assert not result.success
    assert "Build failed" in result.error


def test_unknown_language_is_refused():
    result = run_files({"a.cob": "X"}, "a.cob", language="cobol")
    assert not result.success
    assert "cobol" in result.error


def test_language_aliases_resolve():
    """The planner may answer 'js' or 'PY'; both must reach the same spec."""
    _skip_if_missing(["node"])
    result = run_files({"main.js": "console.log(1+1)"}, "main.js", language="JS")
    assert result.success, result.error


# --- execute_code: validation gate ---------------------------------------

def test_valid_code_runs():
    result = execute_code("", allow_exec=True, language="python",
                          files_content={"main.py": "print('hello')"}, entry="main.py")
    assert result.success and result.validated
    assert "hello" in result.output


def test_broken_code_is_blamed_not_excused():
    """Broken code: success=False, but validated stays True — we did check it."""
    result = execute_code("", allow_exec=True, language="python",
                          files_content={"bad.py": "def f(:"}, entry="bad.py")
    assert not result.success
    assert result.validated
    assert "bad.py" in result.error


def test_missing_toolchain_is_unchecked_not_broken():
    """No validator toolchain: the code is not blamed, but it is not run either."""
    if shutil.which("ruby"):
        pytest.skip("ruby installed, validation would succeed")
    result = execute_code("", allow_exec=True, language="ruby",
                          files_content={"main.rb": "puts 1"}, entry="main.rb")
    assert result.success          # not the code's fault
    assert not result.validated    # but nothing was verified
    assert not result.output       # and nothing was executed


def test_unknown_language_is_unchecked():
    result = execute_code("", allow_exec=True, language="cobol",
                          files_content={"a.cob": "X"}, entry="a.cob")
    assert result.success
    assert not result.validated


def test_execution_gate_blocks_running():
    """allow_exec=False validates but never runs the code."""
    result = execute_code("", allow_exec=False, language="python",
                          files_content={"main.py": "print('should not run')"},
                          entry="main.py")
    assert result.success
    assert "should not run" not in result.output


def test_snippet_without_files_still_runs():
    """A bare string is treated as a one-file program."""
    result = execute_code("print('snippet')", allow_exec=True, language="python")
    assert result.success
    assert "snippet" in result.output


def test_supported_languages_listed():
    languages = supported_run_languages()
    assert "python" in languages
    assert languages == sorted(languages)   # stable order for the error message