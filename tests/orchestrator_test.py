# tests/orchestrator_test.py
import os

import pytest

from codeagent.executor import execute_code
from codeagent.orchestrator import run_agent_loop
from codeagent.static_code_validation import definite_static_validate

# Integration tests below drive a full agent loop and require a running Ollama
# server. They are skipped by default; set RUN_INTEGRATION=1 to run them.
_integration = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION"),
    reason="set RUN_INTEGRATION=1 to run (needs a running Ollama server)",
)


def test_static_validate_ok():
    result = definite_static_validate("def foo(): pass", "python")
    assert result.success is True


def test_static_validate_error():
    result = definite_static_validate("def foo(: pass", "python")  # syntax error
    assert result.success is False
    assert "SyntaxError" in result.error


def test_static_validate_unsupported_language():
    result = definite_static_validate("package main", "go")
    assert result.success is False
    assert "go" in result.error


def test_execute_code_ok():
    result = execute_code("print('hello')", allow_exec=True)
    assert result.success is True
    assert "hello" in result.output


def test_execute_code_timeout():
    result = execute_code("while True: pass", allow_exec=True, timeout=1)
    assert result.success is False
    assert "Timeout" in result.error


@_integration
def test_sum_of_numbers():
    task = "напиши функцию sum_of_numbers(n), которая возвращает сумму чисел от 1 до n"
    state = run_agent_loop(task, allow_exec=True, max_iterations=3, verbose=False)
    assert state.code is not None
    assert "sum_of_numbers" in state.code
    assert state.test_results is not None
    assert "Returncode: 0" in state.test_results
    assert state.done is True


@_integration
def test_failing_code():
    task = "напиши функцию divide(a, b), которая возвращает a / b"
    state = run_agent_loop(task, allow_exec=True, max_iterations=3, verbose=False)
    assert state.code is not None
    assert state.done is True
    assert "Returncode: 0" in state.test_results