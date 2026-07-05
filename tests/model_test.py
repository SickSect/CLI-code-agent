"""Quick test for Ollama client with config."""

from src.codeagent.client import get_client, list_models


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


if __name__ == "__main__":
    test_ollama()