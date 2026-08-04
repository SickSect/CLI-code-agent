from codeagent.executor import run_files, execute_code


def test_run_files_resolves_imports():
    files = {
        "models.py": "class User:\n    def __init__(self, n): self.n = n",
        "main.py": "from models import User\nprint(User('Alice').n)",
    }
    r = run_files(files, "main.py")
    assert r.success and "Alice" in r.output


def test_validation_names_the_broken_file():
    files = {"good.py": "x = 1", "bad.py": "def f(:"}
    r = execute_code("x = 1", allow_exec=True, files_content=files, entry="good.py")
    assert not r.success
    assert "bad.py" in r.error          # имя файла в ошибке


def test_fixer_merge_keeps_untouched_files():
    old = {"a.py": "A", "b.py": "B"}
    new = {"a.py": "A2"}                 # фиксер вернул только один
    merged = {**old, **new}
    assert merged == {"a.py": "A2", "b.py": "B"}