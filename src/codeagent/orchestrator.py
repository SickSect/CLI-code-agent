from typing import Optional

from src.codeagent.agent import Agent
from src.codeagent.client import ModelClient
from src.codeagent.state import AgentState


class Orchestrator:
    def __init__(self, client: ModelClient,
                 coder_prompt_file_path: Optional[str] = "/system_prompts/coder_prompt_base.md",
                 fixer_prompt_file_path: Optional[str] = "/system_prompts/fixer_prompt_base.md",
                 planner_prompt_file_path: Optional[str] = "/system_prompts/planner_prompt_base.md",
                 reviewer_prompt_file_path: Optional[str] = "/system_prompts/reviewer_prompt_base.md"):


        with open(coder_prompt_file_path, 'r', encoding='utf-8') as file:
            coder_prompt = file.read()
        self.coder = Agent("coder", client, coder_prompt)

        with open(fixer_prompt_file_path, 'r', encoding='utf-8') as file:
            fixer_prompt = file.read()
        self.fixer = Agent("fixer", client, fixer_prompt)

        with open(planner_prompt_file_path, 'r', encoding='utf-8') as file:
            planner_prompt = file.read()
        self.planner = Agent("planner", client, planner_prompt)

        with open(reviewer_prompt_file_path, 'r', encoding='utf-8') as file:
            reviewer_prompt = file.read()
        self.reviewer = Agent("coder", client, reviewer_prompt)



