from codeagent.executor import execute_code


def test_docker():
    result = execute_code("print('hello world')", backend='docker')
    assert result.output == "hello world\n"

if __name__ == "__main__":
    test_docker()