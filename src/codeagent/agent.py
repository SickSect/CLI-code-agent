from typing import Optional, Dict

from codeagent.client import ModelClient
from codeagent.state import AgentState


class Agent:
    def __init__(self, name: str, client: ModelClient, system_prompt: str):
        self.name = name
        self.client = client
        self.system_prompt = system_prompt

    def run(self, user_prompt: str, context: Optional[Dict] = None) -> str:
        """Выполняет задачу агента, формируя полный промпт."""
        full_prompt = self._build_prompt(user_prompt, context)
        return self.client.generate(full_prompt, self.system_prompt)

    def _build_prompt(self, user_prompt: str, context: Optional[Dict]) -> str:
        """Формирует промпт из user_prompt и контекста (ключ-значение)."""
        if not context:
            return user_prompt

        # Собираем строки контекста
        context_lines = []
        for key, value in context.items():
            context_lines.append(f"{key}: {value}")
        context_str = "\n".join(context_lines)

        # Объединяем с user_prompt
        return f"{context_str}\n\n{user_prompt}"

    def coder(self, state: AgentState, context: Optional[Dict] = None) -> AgentState:
        """Агент-кодер: генерирует код по задаче."""
        state.role = "coder"

        # Если контекст не передан, используем системный промпт
        if context is None:
            context = {"system_prompt": self.system_prompt}

        # Генерируем код
        code = self.run(
            user_prompt=state.task,
            context=context
        )
        state.code = code
        return state