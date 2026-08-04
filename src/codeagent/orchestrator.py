import json
from pathlib import Path
from typing import Optional

from codeagent.agent import Agent
from codeagent.client import ModelClient, get_client
from codeagent.code_agent_logger import CodeAgentLogger
from codeagent.executor import execute_code, strip_code_fences
from codeagent.state import AgentState

# Name of the generated test file. It is written next to the product files so
# plain imports (e.g. `from service import X`) resolve, and it is what we run.
TESTS_FILE = "_tests.py"


def _files_to_text(files_content: dict) -> str:
    """Render {path: content} as readable text for a prompt."""
    if not files_content:
        return ""
    return "\n\n".join(f"### {path}\n{content}" for path, content in files_content.items())


def _parse_files(raw: str, fallback_path: str) -> dict:
    """Parse a coder/fixer answer ([{path, content}, ...]) into {path: content}.

    Falls back to treating the whole answer as a single file when the model
    fails to produce valid JSON.
    """
    cleaned = strip_code_fences(raw)
    try:
        files = json.loads(cleaned)
        return {f["path"]: f["content"] for f in files}
    except (json.JSONDecodeError, KeyError, TypeError):
        return {fallback_path: cleaned}


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

        # Создаём агентов
        self.coder = Agent("coder", client, coder_prompt, 0.3)
        self.fixer = Agent("fixer", client, fixer_prompt, 0.2)
        self.planner = Agent("planner", client, planner_prompt, 0.7)
        self.reviewer = Agent("reviewer", client, reviewer_prompt, 0.1)
        self.tester = Agent("tester", client, tester_prompt, 0.3)


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


def run_planer(state: AgentState, task: str, orch: Orchestrator, verbose):
    """Planner: returns JSON {language, entry, files, plan}."""
    logger = CodeAgentLogger(verbose=verbose)
    logger.step("Planner", input_summary=task)

    if state.previous_files:
        planner_input = (
            f"Previous code:\n{_files_to_text(state.previous_files)}\n\nTask: {task}"
        )
    else:
        planner_input = task
    raw_plan = orch.planner.run(user_prompt=planner_input, context={"task": task})

    cleaned = strip_code_fences(raw_plan)
    try:
        data = json.loads(cleaned)
        state.lang = data["language"].lower()
        state.entry = data["entry"]
        state.files = data["files"]
        plan_steps = data["plan"]
        state.plan = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(plan_steps))
    except (json.JSONDecodeError, KeyError, AttributeError):
        state.lang = "python"
        state.entry = "main.py"
        state.files = [{"path": "main.py", "purpose": task}]
        state.plan = raw_plan
    logger.debug(f"Language: {state.lang}\nEntry: {state.entry}\nPlan:\n{state.plan}")
    return state


def run_coder(state: AgentState, task: str, orch: Orchestrator, verbose):
    """Coder: returns JSON [{path, content}, ...] for every planned file."""
    logger = CodeAgentLogger(verbose=verbose)

    files_list = "\n".join(
        f"- {f.get('path')}: {f.get('purpose', '')}" for f in (state.files or [])
    )
    base_prompt = (
        f"Task: {task}\n"
        f"Plan:\n{state.plan}\n"
        f"Files to create:\n{files_list}\n"
        f"Entry file: {state.entry}"
    )
    if state.previous_files:
        coder_prompt = (
            f"Previous code:\n{_files_to_text(state.previous_files)}\n\n"
            f"The task below may continue or modify the code above.\n"
            f"{base_prompt}"
        )
    else:
        coder_prompt = base_prompt

    logger.step("Coder", input_summary=f"Task: {task}\nFiles: {len(state.files or [])}")
    raw_code = orch.coder.run(user_prompt=coder_prompt, context={"plan": state.plan})
    state.files_content = _parse_files(raw_code, state.entry)
    state.code = state.files_content.get(state.entry, "")
    logger.debug(f"Generated files: {list(state.files_content)}")
    return state


def run_tester(state: AgentState, task: str, orch: Orchestrator, verbose):
    """Tester: writes a standalone test module that imports the product files."""
    logger = CodeAgentLogger(verbose=verbose)
    logger.step("Tester", input_summary=f"Files: {list(state.files_content)}")

    tester_prompt = (
        f"Task: {task}\n"
        f"Code:\n{_files_to_text(state.files_content)}\n"
        f"Write the full content of {TESTS_FILE}: import what you need from the "
        f"modules above by module name, then assert on their return values."
    )
    state.asserts = strip_code_fences(
        orch.tester.run(user_prompt=tester_prompt, context={"code": state.code})
    )
    logger.debug(f"Asserts:\n{state.asserts}")
    return state


def run_execution(state: AgentState, allow_exec, timeout, backend, verbose):
    """Run the product files plus the test module; the tests are the entry point."""
    logger = CodeAgentLogger(verbose=verbose)
    logger.step("Executor", input_summary="Running the code with asserts...")

    files_to_run = dict(state.files_content)   # copy: state keeps only product files
    files_to_run[TESTS_FILE] = state.asserts   # tests live next to the modules
    logger.debug(f"Backend: {backend}, files: {list(files_to_run)}")
    exec_result = execute_code(state.asserts,
                               allow_exec=allow_exec,
                               timeout=timeout,
                               backend=backend,
                               language=state.lang,
                               files_content=files_to_run,
                               entry=TESTS_FILE)
    state.test_results = (
        f"STDOUT:\n{exec_result.output}\n"
        f"STDERR:\n{exec_result.error}\n"
        f"Returncode: {exec_result.returncode}"
    )
    logger.debug(
        f"Execution result: success={exec_result.success}, returncode={exec_result.returncode}"
    )
    if not exec_result.success:
        logger.warning(f"Execution failed: {exec_result.error}")
    return state


def run_review(state: AgentState, task, orch: Orchestrator, verbose):
    """Reviewer: verdict based on all files plus the real execution results."""
    logger = CodeAgentLogger(verbose=verbose)
    logger.step("Reviewer", input_summary=f"Files: {list(state.files_content)}")

    review = orch.reviewer.run(
        user_prompt=(
            f"Task: {task}\n"
            f"Code:\n{_files_to_text(state.files_content)}\n"
            f"Execution results:\n{state.test_results}"
        ),
        context={"code": state.code, "exec_results": state.test_results}
    )
    state.review = review
    logger.debug(f"Review:\n{review}")
    return state


def run_fixer(state: AgentState, task, orch: Orchestrator, verbose):
    """Fixer: returns the corrected files in the same JSON shape as the coder."""
    logger = CodeAgentLogger(verbose=verbose)
    logger.step("Fixer", input_summary=f"Review length: {len(state.review)} chars")

    fixed = orch.fixer.run(
        user_prompt=(
            f"Task: {task}\n"
            f"Code:\n{_files_to_text(state.files_content)}\n"
            f"Entry file: {state.entry}\n"
            f"Review comments:\n{state.review}"
        ),
        context={"review": state.review}
    )
    fixed_files = _parse_files(fixed, state.entry)
    state.files_content = {**state.files_content, **fixed_files}
    state.code = state.files_content.get(state.entry, "")
    logger.debug(f"Fixed files: {list(state.files_content)}")
    return state


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
    state.task = task

    # 1. Планирование
    state = run_planer(state, task, orch, verbose)

    # 2. Coder
    state = run_coder(state, task, orch, verbose)

    # 2b. Tester — один раз, тесты к этому коду
    state = run_tester(state, task, orch, verbose)

    # 3. Цикл ревью-фикс
    for i in range(max_iterations):
        logger.info(f"Iteration {i + 1}/{max_iterations}")

        state = run_execution(state, allow_exec, timeout, backend, verbose)
        state = run_review(state, task, orch, verbose)

        if _is_approved(state.review):
            state.done = True
            logger.info("Reviewer approved the code. Done!")
            break

        state = run_fixer(state, task, orch, verbose)
        state.iteration = i + 1

    logger.info("Task finished.")
    return state