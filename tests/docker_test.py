import pytest

from codeagent.executor import execute_code, _docker_available

# This test actually runs a container, so it needs Docker installed and running.
# It is skipped automatically when Docker is unavailable.
pytestmark = pytest.mark.skipif(
    not _docker_available(5), reason="Docker not available"
)


def test_docker():
    result = execute_code(
        "print('hello world')", allow_exec=True, backend="docker"
    )
    assert result.output == "hello world\n"