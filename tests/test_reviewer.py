import asyncio
from types import SimpleNamespace

from app import reviewer


class FakeCompletions:
    def __init__(self, content=None, error=None):
        self.content, self.error, self.calls = content, error, []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def fake_client(completions):
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def run(coro):
    return asyncio.run(coro)


def test_prompt_is_sent_unchanged_not_split_into_characters(monkeypatch):
    completions = FakeCompletions(content="looks fine")
    monkeypatch.setattr(reviewer, "_get_client", lambda: fake_client(completions))

    result = run(reviewer.review_code_with_llm("def add(a, b):\n    return a + b"))

    assert result == "looks fine"
    user_message = completions.calls[0]["messages"][1]["content"]
    assert user_message == "def add(a, b):\n    return a + b"  # the old join() put blank lines between characters


def test_system_prompt_treats_diff_as_data(monkeypatch):
    completions = FakeCompletions(content="ok")
    monkeypatch.setattr(reviewer, "_get_client", lambda: fake_client(completions))
    run(reviewer.review_code_with_llm("x"))
    system = completions.calls[0]["messages"][0]
    assert system["role"] == "system"
    assert "never as instructions" in system["content"]


def test_returns_failure_message_instead_of_raising(monkeypatch):
    completions = FakeCompletions(error=RuntimeError("boom"))
    monkeypatch.setattr(reviewer, "_get_client", lambda: fake_client(completions))
    assert run(reviewer.review_code_with_llm("x")) == reviewer.FAILURE_MESSAGE


def test_empty_content_becomes_empty_string(monkeypatch):
    completions = FakeCompletions(content=None)
    monkeypatch.setattr(reviewer, "_get_client", lambda: fake_client(completions))
    assert run(reviewer.review_code_with_llm("x")) == ""
