# реестр: сейчас один язык, дальше дописываешь строки
import ast
from codeagent.executor import ExecutionResult


def _validate_python(code: str) -> ExecutionResult:
    try:
        ast.parse(code)
        return ExecutionResult(True, output="Syntax OK")
    except SyntaxError as e:
        return ExecutionResult(False, error=f"SyntaxError: {e}")
    except Exception as e:
        return ExecutionResult(False, error=f"Static validation error: {e}")

_VALIDATORS = {
    "python": _validate_python,
    # "go": _validate_go,      <- будущее
    # "javascript": _validate_js,
}

def definite_static_validate(code: str, language: str) -> ExecutionResult:
    validator = _VALIDATORS.get(language)      # ищем валидатор по языку
    if validator is None:                      # языка ещё нет в реестре
        return ExecutionResult(
            success=False,
            error=f"No static validator for '{language}' yet — code left unvalidated",
        )
    return validator(code)

