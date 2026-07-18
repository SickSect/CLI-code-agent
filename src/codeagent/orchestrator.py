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
                 reviewer_prompt_file_path: Optional[str] = None):

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

        # Читаем промпты
        with open(coder_prompt_file_path, 'r', encoding='utf-8') as file:
            coder_prompt = file.read()
        with open(fixer_prompt_file_path, 'r', encoding='utf-8') as file:
            fixer_prompt = file.read()
        with open(planner_prompt_file_path, 'r', encoding='utf-8') as file:
            planner_prompt = file.read()
        with open(reviewer_prompt_file_path, 'r', encoding='utf-8') as file:
            reviewer_prompt = file.read()

        # Создаём агентов (исправлено: reviewer теперь "reviewer", а не "coder")
        self.coder = Agent("coder", client, coder_prompt)
        self.fixer = Agent("fixer", client, fixer_prompt)
        self.planner = Agent("planner", client, planner_prompt)
        self.reviewer = Agent("reviewer", client, reviewer_prompt)


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


def run_agent_loop(task: str, allow_exec: bool = False, max_iterations: int = 5, verbose: bool = True) -> AgentState:
    logger = CodeAgentLogger(verbose=verbose)
    logger.info(f"Starting task: {task}")

    client = get_client()
    orch = Orchestrator(client)
    state = AgentState(max_iterations)
    state.task = task

    # 1. Планирование
    logger.step("Planner", input_summary=task)
    plan = orch.planner.run(user_prompt=task, context={"task": task})
    state.plan = plan
    logger.debug(f"Plan:\n{plan}")

    # 2. Coder
    logger.step("Coder", input_summary=f"Task: {task}\nPlan: {plan}")
    code = orch.coder.run(user_prompt=f"Task: {task}\nPlan: {plan}", context={"plan": plan})
    state.code = strip_code_fences(code)
    logger.debug(f"Generated code:\n{code}")

    # 3. Цикл ревью-фикс
    for i in range(max_iterations):
        logger.info(f"Iteration {i+1}/{max_iterations}")

        # --- ВЫПОЛНЕНИЕ КОДА ---
        logger.step("Executor", input_summary="Running the code...")
        exec_result = execute_code(state.code, allow_exec=allow_exec, timeout=10)
        # Сохраняем результаты выполнения в state
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
        # Передаём в ревью код, задачу и результаты выполнения
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