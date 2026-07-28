from unittest.mock import MagicMock, patch
from codeagent.state import AgentState


def _fake_orch(code_answer, asserts):
    """Orchestrator со заглушенными агентами."""
    orch = MagicMock()
    orch.planner.run.return_value = '{"language": "python", "plan": ["s"]}'
    orch.coder.run.return_value = code_answer
    orch.tester.run.return_value = asserts
    orch.reviewer.run.return_value = "OK"
    orch.fixer.run.return_value = code_answer
    return orch


def test_asserts_pass_on_correct_code():
    good = "def add(a, b):\n    return a + b"
    tests = "assert add(2, 3) == 5\nassert add(0, 0) == 0"
    with patch("codeagent.orchestrator.Orchestrator", return_value=_fake_orch(good, tests)), \
         patch("codeagent.orchestrator.get_client"):
        from codeagent.orchestrator import run_agent_loop
        state = run_agent_loop("add two numbers", allow_exec=True, max_iterations=1, verbose=False)
    assert "Returncode: 0" in state.test_results     # тесты прошли


def test_asserts_fail_on_wrong_code():
    bad = "def add(a, b):\n    return a - b"          # баг: минус вместо плюса
    tests = "assert add(2, 3) == 5"
    with patch("codeagent.orchestrator.Orchestrator", return_value=_fake_orch(bad, tests)), \
         patch("codeagent.orchestrator.get_client"):
        from codeagent.orchestrator import run_agent_loop
        state = run_agent_loop("add two numbers", allow_exec=True, max_iterations=1, verbose=False)
    assert "Returncode: 0" not in state.test_results  # assert упал
    assert "AssertionError" in state.test_results