"""Quick test for Ollama client with config."""
from altair.utils import Optional

from src.codeagent.agent import Agent
from src.codeagent.client import get_client, list_models
from src.codeagent.state import AgentState


def test_ollama():
    client = get_client()

    print(f"Current model: {client.model}")
    print(f"Ollama running: {client.is_running()}")

    if client.is_running():
        print(f"Model available: {client.is_model_available()}")

        if client.is_model_available():
            print("\nGenerating...")
            response = client.generate("Write a hello world in Python")
            print(response)
        else:
            print(f"\n❌ Model '{client.model}' not downloaded.")
            print("Available models:")
            for m in list_models():
                print(f"  - {m}")
            print(f"\nRun: ollama pull {client.model}")
    else:
        print("\n❌ Ollama not running. Start with:")
        print("  ollama serve")

def test_coder():
    state = AgentState()
    state.task = "напиши функцию, которая считает сумму чисел от 1 до N"
    state.plan = "функция принимаем аргумент формата int, возвращает int"
    system_prompt = """Ты — опытный разработчик. Напиши код на Python по следующему плану.
    Код должен быть готов к выполнению. Не добавляй лишних комментариев, только код.
    Если нужны зависимости — укажи их в комментарии."""


    client = get_client()
    if client.is_running():
        print(f"Model available: {client.is_model_available()}")

        if client.is_model_available():
            print("\nGenerating...")

            agent = Agent("coder", client, system_prompt)
            response = agent.coder(state)
            print(response.code)
        else:
            print(f"\n❌ Model '{client.model}' not downloaded.")
            print("Available models:")
            for m in list_models():
                print(f"  - {m}")
            print(f"\nRun: ollama pull {client.model}")
    else:
        print("\n❌ Ollama not running. Start with:")
        print("  ollama serve")

if __name__ == "__main__":
    test_ollama()