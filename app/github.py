import os

import httpx

API_URL = "https://api.github.com"
PER_PAGE = 100                 # maximum GitHub allows per page (the default is only 30)
MAX_FILES = 300                # stop paging here to bound work and cost (GitHub itself caps at 3000)
COMMENT_LIMIT = 60_000         # GitHub rejects comments over 65,536 characters; stay safely below


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(15.0))


async def get_pr_files(repo: str, pr_number: int, max_files: int = MAX_FILES) -> list:
    """All changed files of a pull request (paginated). Raises httpx.HTTPError on any failure."""
    files: list = []
    page = 1
    async with _client() as client:
        while len(files) < max_files:
            resp = await client.get(
                f"{API_URL}/repos/{repo}/pulls/{pr_number}/files",
                headers=_headers(),
                params={"per_page": PER_PAGE, "page": page},
            )
            resp.raise_for_status()
            batch = resp.json()
            files.extend(batch)
            if len(batch) < PER_PAGE:
                break
            page += 1
    return files[:max_files]


async def post_pr_comment(repo: str, pr_number: int, comment: str) -> dict:
    """Post a PR comment. Raises httpx.HTTPError if GitHub rejects it, so callers can react."""
    if len(comment) > COMMENT_LIMIT:
        comment = comment[:COMMENT_LIMIT] + "\n\n_Review truncated to fit GitHub's comment size limit._"
    async with _client() as client:
        resp = await client.post(
            f"{API_URL}/repos/{repo}/issues/{pr_number}/comments",
            headers=_headers(),
            json={"body": comment},
        )
        resp.raise_for_status()
        return resp.json()
