"""Ollama client wrapper for codeagent."""

import os
from pathlib import Path
from typing import Optional

import ollama
import yaml


class ModelClient:
    """Client for interacting with local model instance."""

    def __init__(
        self,
        model: Optional[str] = None,
        host: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        config = self._load_config()

        self.model = (
            model
            or os.getenv("CODEAGENT_MODEL")
            or config.get("model", "qwen2.5-coder:7b")
        )
        self.timeout = (
            timeout
            or int(os.getenv("CODEAGENT_TIMEOUT", 120))
            or config.get("timeout", 120)
        )
        self.host = (
            host
            or os.getenv("MODEL_HOST")
            or config.get("host", "http://localhost:11434")
        )
        self.client = ollama.Client(host=self.host)

    @staticmethod
    def _load_config() -> dict:
        """Load config from ~/.codeagent/config.yaml."""
        config_path = Path.home() / ".codeagent" / "config.yaml"
        if config_path.exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    @classmethod
    def from_env(cls, model: Optional[str] = None) -> "ModelClient":
        """Create client with optional model override."""
        return cls(model=model)

    def is_running(self) -> bool:
        """Checking is server is running."""
        try:
            self.client.list()
            return True
        except Exception:
            return False

    def is_model_available(self, model: Optional[str] = None) -> bool:
        """Check if the configured model is downloaded."""
        try:
            models = self.client.list()
            target = model or self.model
            return any(m.model == target for m in models.models)
        except Exception:
            return False

    def list_available_models(self) -> list[str]:
        """List all downloaded models."""
        try:
            models = self.client.list()
            return [m.model for m in models.models]
        except Exception:
            return []

    def generate(self,
                 prompt: str,
                 system_prompt:
                 Optional[str] = None,
                 temperature: float = 0.5,
                 num_ctx: int = 4096,
                 seed: int = None) -> str:
        """Send a prompt to Model and get the response."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        options = {
                "temperature": temperature,
                "num_ctx": num_ctx
            }
        if seed is not None:
            options["seed"] = seed

        response = self.client.chat(
            model=self.model,
            messages=messages,
            stream=False,
            options=options
        )
        return response["message"]["content"]

    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None):
        """Stream response from Model."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = self.client.chat(
            model=self.model,
            messages=messages,
            stream=True,
        )

        for chunk in stream:
            yield chunk["message"]["content"]


# Простой API
_default_client: Optional[ModelClient] = None


def get_client(model: Optional[str] = None) -> ModelClient:
    """Get or create default client."""
    global _default_client
    if _default_client is None or model:
        _default_client = ModelClient.from_env(model=model)
    return _default_client


def generate(prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None) -> str:
    """Quick one-off generation."""
    return get_client(model).generate(prompt, system_prompt)


def generate_stream(prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None):
    """Quick one-off streaming generation."""
    return get_client(model).generate_stream(prompt, system_prompt)


def list_models() -> list[str]:
    """List available models."""
    return get_client().list_available_models()