# tests/test_orchestrator.py
from codeagent.executor import static_validate, execute_code
from codeagent.orchestrator import run_agent_loop


def test_sum_of_numbers():
    """Проверяем, что агент генерирует функцию sum_of_numbers и она работает."""
    task = "напиши функцию sum_of_numbers(n), которая возвращает сумму чисел от 1 до n"
    state = run_agent_loop(task, allow_exec=True, max_iterations=3, verbose=False)

    # Проверяем, что код был сгенерирован
    assert state.code is not None
    assert "sum_of_numbers" in state.code

    # Проверяем, что выполнение прошло успешно
    assert state.test_results is not None
    assert "Returncode: 0" in state.test_results

    # Проверяем, что ревьюер одобрил код (state.done == True)
    assert state.done is True

    # Дополнительно можно проверить, что в выводе есть правильный результат
    # Например, если код напечатал результат, можно проверить stdout
    # Но в нашем случае мы не печатаем ничего, поэтому просто проверяем returncode

def test_static_validate_ok():
    code = "def foo(): pass"
    result = static_validate(code)
    assert result.success is True


def test_static_validate_error():
    code = "def foo(: pass"  # синтаксическая ошибка
    result = static_validate(code)
    assert result.success is False
    assert "SyntaxError" in result.error


def test_execute_code_ok():
    code = "print('hello')"
    result = execute_code(code, allow_exec=True)
    assert result.success is True
    assert "hello" in result.output


def test_execute_code_timeout():
    code = "while True: pass"
    result = execute_code(code, allow_exec=True, timeout=1)
    assert result.success is False
    assert "Timeout" in result.error


def test_failing_code():
    """Проверяем, что агент исправляет код, если он упал."""
    task = "напиши функцию divide(a, b), которая возвращает a / b"
    state = run_agent_loop(task, allow_exec=True, max_iterations=3, verbose=False)

    # Проверяем, что код есть
    assert state.code is not None

    # Если код написан без обработки деления на ноль, он может упасть
    # Но агент должен исправить это, и в итоге код должен выполняться
    # Проверяем, что после итераций код стал рабочим
    assert state.done is True
    assert "Returncode: 0" in state.test_results