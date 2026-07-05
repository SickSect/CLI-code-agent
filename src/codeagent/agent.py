# agent.py
from typing import Optional, Dict
from client import ModelClient

class Agent:
    def __init__(self, name: str, client: ModelClient, system_prompt: str):
        self.name = name
        self.client = client
        self.system_prompt = system_prompt

    def run(self, user_prompt: str, context: Optional[Dict] = None) -> str:
        """Выполняет задачу агента."""
        full_prompt = self._build_prompt(user_prompt, context)
        return self.client.generate(full_prompt, self.system_prompt)

    def _build_prompt(self, user_prompt: str, context: Optional[Dict]) -> str:
        """Формирует промпт с учётом контекста."""
        # Можно переопределить в наследниках
        return user_prompt