import json
from pathlib import Path
from typing import Optional

from codeagent.agent import Agent
from codeagent.client import ModelClient, get_client
from codeagent.code_agent_logger import CodeAgentLogger
from codeagent.executor import execute_code, strip_code_fences
from codeagent.state import AgentState


class Orchestrator:
    def __init__(self, client: ModelClient,
                 coder_prompt_file_path: Optional[str] = None,
                 fixer_prompt_file_path: Optional[str] = None,
                 planner_prompt_file_path: Optional[str] = None,
                 reviewer_prompt_file_path: Optional[str] = None,
                 tester_prompt_file_path: Optional[str] = None
                 ):

        # Базовая папка — где лежит этот файл (orchestrator.py)
        base_dir = Path(__file__).parent

        # Если пути не переданы, используем стандартные имена в папке system_prompts
        if coder_prompt_file_path is None:
            coder_prompt_file_path = base_dir / "system_prompts" / "coder_prompt_base.md"
        if fixer_prompt_file_path is None:
            fixer_prompt_file_path = base_dir / "system_prompts" / "fixer_prompt_base.md"
        if planner_prompt_file_path is None:
            planner_prompt_file_path = base_dir / "system_prompts" / "planner_prompt_base.md"
        if reviewer_prompt_file_path is None:
            reviewer_prompt_file_path = base_dir / "system_prompts" / "reviewer_prompt_base.md"
        if tester_prompt_file_path is None:
            tester_prompt_file_path = base_dir / "system_prompts" / "tester_prompt_base.md"

        # Читаем промпты
        with open(coder_prompt_file_path, 'r', encoding='utf-8') as file:
            coder_prompt = file.read()
        with open(fixer_prompt_file_path, 'r', encoding='utf-8') as file:
            fixer_prompt = file.read()
        with open(planner_prompt_file_path, 'r', encoding='utf-8') as file:
            planner_prompt = file.read()
        with open(reviewer_prompt_file_path, 'r', encoding='utf-8') as file:
            reviewer_prompt = file.read()
        with open(tester_prompt_file_path, 'r', encoding='utf-8') as file:
            tester_prompt = file.read()

        # Создаём агентов (исправлено: reviewer теперь "reviewer", а не "coder")
        self.coder = Agent("coder", client, coder_prompt, 0.3)
        self.fixer = Agent("fixer", client, fixer_prompt, 0.2)
        self.planner = Agent("planner", client, planner_prompt, 0.7)
        self.reviewer = Agent("reviewer", client, reviewer_prompt,0.1)
        self.tester = Agent("tester", client, tester_prompt,0.3)


def _is_approved(review: str) -> bool:
    """Return True only when the reviewer clearly signalled approval.

    The reviewer is instructed to answer with exactly "OK" on success. We look
    at the first non-empty line and normalise trivial formatting (surrounding
    quotes, backticks, asterisks, a trailing period) before comparing, so that
    "NOT OK" or "OK, but fix X" are NOT mistaken for a pass.
    """
    stripped = review.strip()
    if not stripped:
        return False
    first_line = stripped.splitlines()[0]
    cleaned = first_line.strip(" \t\"'`.*").upper()
    return cleaned == "OK"


def run_agent_loop(task: str,
                   allow_exec: bool = False,
                   max_iterations: int = 5,
                   verbose: bool = True,
                   backend: str = "subprocess",
                   timeout=10,
                   last_state: AgentState = None) -> AgentState:
    logger = CodeAgentLogger(verbose=verbose)
    logger.info(f"Starting task: {task}")

    client = get_client()
    orch = Orchestrator(client)
    if last_state is None:
        state = AgentState(max_iterations)
    else:
        state = last_state
    state.leave_prev_code()

    # 1. Планирование — планировщик отдаёт JSON {"language": ..., "plan": [...]}
    if state.previous_code:
        planner_input = f"Previous code:\n{state.previous_code}\n\nTask: {task}"
    else:
        planner_input = task
    raw_plan = orch.planner.run(user_prompt=planner_input, context={"task": task})

    cleaned = strip_code_fences(raw_plan)          # снять ```json ... ``` если есть
    try:
        data = json.loads(cleaned)
        state.lang = data["language"].lower()      # правильный ключ + нормализация
        plan_steps = data["plan"]                  # массив шагов
    except (json.JSONDecodeError, KeyError, AttributeError):
        state.lang = "python"                      # фолбэк: не распарсили — Python
        plan_steps = [raw_plan]                    # хоть что-то отдать коудеру

    # план — массив шагов, коудеру нужна строка: склеиваем в нумерованный список
    state.plan = "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan_steps))
    logger.debug(f"Language: {state.lang}\nPlan:\n{state.plan}")

    # 2. Coder
    if state.previous_code is not None:
        coder_prompt = (
            f"Previous code:\n{state.previous_code}\n\n"
            f"The task below may continue or modify the code above.\n"
            f"Task: {task}\nPlan: {state.plan}"
        )
    else:
        coder_prompt = f"Task: {task}\nPlan: {state.plan}"
    logger.step("Coder", input_summary=f"Task: {task}\nPlan: {state.plan}")
    code = orch.coder.run(user_prompt=coder_prompt, context={"plan": state.plan})
    state.code = strip_code_fences(code)
    logger.debug(f"Generated code:\n{code}")

    # 2. Coder
    if state.previous_code is not None:
        coder_prompt = (
            f"Previous code:\n{state.previous_code}\n\n"
            f"The task below may continue or modify the code above.\n"
            f"Task: {task}\nPlan: {state.plan}"
        )
    else:
        coder_prompt = f"Task: {task}\nPlan: {state.plan}"
    logger.step("Coder", input_summary=f"Task: {task}\nPlan: {state.plan}")
    code = orch.coder.run(user_prompt=coder_prompt, context={"plan": state.plan})
    state.code = strip_code_fences(code)
    logger.debug(f"Generated code:\n{code}")

    # 2b. Tester — один раз, assert'ы к этому коду
    logger.step("Tester", input_summary=f"Code length: {len(state.code)} chars")
    tester_prompt = (
        f"Task: {task}\n"
        f"Code:\n{state.code}\n"
        f"Write assertions that verify this code."
    )
    state.asserts = strip_code_fences(
        orch.tester.run(user_prompt=tester_prompt, context={"code": state.code})
    )
    logger.debug(f"Asserts:\n{state.asserts}")

    # 3. Цикл ревью-фикс
    for i in range(max_iterations):
        logger.info(f"Iteration {i + 1}/{max_iterations}")

        # --- ВЫПОЛНЕНИЕ КОДА + ТЕСТОВ ---
        logger.step("Executor", input_summary="Running the code with asserts...")
        code_with_tests = state.code + "\n\n" + state.asserts
        exec_result = execute_code(code_with_tests,
                                   allow_exec=allow_exec,
                                   timeout=timeout,
                                   backend=backend,
                                   language=state.lang)
        state.test_results = (
            f"STDOUT:\n{exec_result.output}\n"
            f"STDERR:\n{exec_result.error}\n"
            f"Returncode: {exec_result.returncode}"
        )
        logger.debug(f"Execution result: success={exec_result.success}, returncode={exec_result.returncode}")
        if not exec_result.success:
            logger.warning(f"Execution failed: {exec_result.error}")

        # --- РЕВЬЮ ---
        logger.step("Reviewer", input_summary=f"Code length: {len(state.code)} chars")
        review = orch.reviewer.run(
            user_prompt=(
                f"Task: {task}\n"
                f"Code:\n{state.code}\n"
                f"Execution results:\n{state.test_results}"
            ),
            context={"code": state.code, "exec_results": state.test_results}
        )
        state.review = review
        logger.debug(f"Review:\n{review}")

        if _is_approved(review):
            state.done = True
            logger.info("Reviewer approved the code. Done!")
            break

        # --- ФИКСЕР ---
        logger.step("Fixer", input_summary=f"Review length: {len(review)} chars")
        fixed = orch.fixer.run(
            user_prompt=(
                f"Task: {task}\n"
                f"Code:\n{state.code}\n"
                f"Review comments:\n{review}"
            ),
            context={"review": review}
        )
        state.code = strip_code_fences(fixed)
        state.iteration = i + 1
        logger.debug(f"Fixed code:\n{fixed}")

    logger.info("Task finished.")
    return state