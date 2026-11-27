import asyncio

import httpx
import pytest

from app import github


def run(coro):
    return asyncio.run(coro)


def use_transport(monkeypatch, handler):
    monkeypatch.setattr(
        github, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


@pytest.fixture(autouse=True)
def token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t0ken")


def test_get_pr_files_reads_every_page(monkeypatch):
    pages = {1: [{"filename": f"a{i}.py"} for i in range(100)], 2: [{"filename": f"b{i}.py"} for i in range(30)]}
    requested = []

    def handler(request):
        page = int(request.url.params["page"])
        requested.append((page, request.url.params["per_page"]))
        return httpx.Response(200, json=pages[page])

    use_transport(monkeypatch, handler)
    files = run(github.get_pr_files("octo/demo", 7))
    assert len(files) == 130
    assert requested == [(1, "100"), (2, "100")]


def test_get_pr_files_stops_at_the_cap(monkeypatch):
    def handler(request):
        return httpx.Response(200, json=[{"filename": f"f{i}.py"} for i in range(100)])

    use_transport(monkeypatch, handler)
    assert len(run(github.get_pr_files("octo/demo", 7, max_files=150))) == 150


def test_get_pr_files_raises_on_http_error(monkeypatch):
    use_transport(monkeypatch, lambda request: httpx.Response(401, json={"message": "Bad credentials"}))
    with pytest.raises(httpx.HTTPStatusError):
        run(github.get_pr_files("octo/demo", 7))


def test_requests_carry_bearer_token_and_api_headers(monkeypatch):
    seen = {}

    def handler(request):
        seen.update(request.headers)
        return httpx.Response(200, json=[])

    use_transport(monkeypatch, handler)
    run(github.get_pr_files("octo/demo", 7))
    assert seen["authorization"] == "Bearer t0ken"
    assert seen["accept"] == "application/vnd.github+json"


def test_post_comment_sends_body(monkeypatch):
    sent = {}

    def handler(request):
        sent["url"] = str(request.url)
        sent["json"] = request.read()
        return httpx.Response(201, json={"id": 1})

    use_transport(monkeypatch, handler)
    assert run(github.post_pr_comment("octo/demo", 7, "hello")) == {"id": 1}
    assert sent["url"].endswith("/repos/octo/demo/issues/7/comments")
    assert b"hello" in sent["json"]


def test_post_comment_raises_when_github_rejects_it(monkeypatch):
    use_transport(monkeypatch, lambda request: httpx.Response(403, json={"message": "forbidden"}))
    with pytest.raises(httpx.HTTPStatusError):
        run(github.post_pr_comment("octo/demo", 7, "hello"))


def test_long_comments_are_truncated(monkeypatch):
    sent = {}

    def handler(request):
        sent["body"] = request.read()
        return httpx.Response(201, json={})

    use_transport(monkeypatch, handler)
    run(github.post_pr_comment("octo/demo", 7, "x" * (github.COMMENT_LIMIT + 500)))
    assert len(sent["body"]) < github.COMMENT_LIMIT + 300
    assert b"truncated" in sent["body"]


def test_missing_token_fails_loudly(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN")
    with pytest.raises(RuntimeError):
        run(github.post_pr_comment("octo/demo", 7, "hello"))
