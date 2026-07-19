"""Tests for ModelClient.generate() options assembly.

These tests never touch a real Ollama server: the underlying client.chat is
replaced with a fake that records the kwargs it was called with. That keeps the
tests fast and deterministic and lets us assert exactly what ended up in the
`options` dict — which is the behaviour we care about here.
"""

from unittest.mock import MagicMock

import pytest

from codeagent.client import ModelClient


@pytest.fixture
def client():
    """A ModelClient whose network client.chat is a controllable fake.

    We bypass __init__ (it would read config and construct a real ollama
    client) and set only the attributes generate() actually uses.
    """
    c = ModelClient.__new__(ModelClient)   # create instance without __init__
    c.model = "test-model"

    fake = MagicMock()
    # A minimal, valid-looking chat response so generate() can index into it.
    fake.chat.return_value = {"message": {"content": "hi"}}
    c.client = fake
    return c


def _options_of_last_call(client) -> dict:
    """Pull the `options` dict out of the most recent client.chat(...) call."""
    _, kwargs = client.client.chat.call_args
    return kwargs["options"]


def test_defaults_have_temperature_and_num_ctx(client):
    client.generate("do something")
    options = _options_of_last_call(client)

    assert options["temperature"] == 0.5   # default
    assert options["num_ctx"] == 4096      # default
    assert "seed" not in options           # seed omitted when not given


def test_seed_included_only_when_set(client):
    client.generate("do something", seed=123)
    options = _options_of_last_call(client)

    assert options["seed"] == 123


def test_passed_values_reach_chat(client):
    client.generate("do something", temperature=0.1, num_ctx=8192, seed=7)
    options = _options_of_last_call(client)

    assert options == {"temperature": 0.1, "num_ctx": 8192, "seed": 7}


def test_return_value_is_message_content(client):
    result = client.generate("do something")
    assert result == "hi"


def test_system_prompt_added_as_first_message(client):
    client.generate("user text", system_prompt="you are a coder")
    _, kwargs = client.client.chat.call_args
    messages = kwargs["messages"]

    assert messages[0] == {"role": "system", "content": "you are a coder"}
    assert messages[1] == {"role": "user", "content": "user text"}