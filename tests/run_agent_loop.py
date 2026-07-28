from unittest.mock import patch
from click.testing import CliRunner

from codeagent.cli import main


class FakeState:
    def __init__(self, code): self.code = code
    done = True


def test_new_clears_context():
    calls = []

    def fake_loop(task, **kwargs):
        calls.append(kwargs.get("last_state"))   # что пришло как память
        return FakeState(f"# {task}")

    with patch("codeagent.cli.run_agent_loop", side_effect=fake_loop):
        # task1 -> /new -> task2 -> /exit
        CliRunner().invoke(main, ["chat"], input="task1\n/new\ntask2\n/exit\n")

    assert calls[0] is None          # первая задача — без памяти
    assert calls[1] is None          # после /new вторая тоже без памяти