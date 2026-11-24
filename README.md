# AI Code Reviewer

An automated code review service that integrates with GitHub to review pull requests using OpenAI GPT models.
It prompts the model to suggest code optimizations and to flag missing tests and security risks.

## Features

- Automatic code review on pull requests
- Python code focused (can be extended)
- Flags performance issues, security risks, and missing tests
- Stores reviews in PostgreSQL
- Posts review comments directly to GitHub PRs
- Optional GitHub Actions integration for CI/CD

## Tech Stack

- **Backend:** Python, FastAPI
- **LLM:** OpenAI API (GPT-4)
- **Database:** PostgreSQL
- **CI/CD:** GitHub Actions
- **Containerization:** Docker, Docker Compose

## How the AI Code Review Works

```text
   [GitHub Pull Request]
             |
             v
     [GitHub Actions / Webhook]
             |
             v
       [FastAPI Service]
             |
             v
      [OpenAI GPT-4 API]  <---- Review Python code
             |
             v
     [PostgreSQL Database]   <---- Store review history
             |
             v
   [GitHub PR Comments]       <---- Post review suggestions
```

## Getting started

Requires Docker.

```bash
git clone https://github.com/surya532/AI-Code-Reviewer.git
cd AI-Code-Reviewer
cp .env.example .env        # then add your keys
docker compose up --build   # API on http://localhost:8000
```

### Configuration
Set these in `.env` (see `.env.example`):

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | Token allowed to read pull requests and post comments |
| `OPENAI_API_KEY` | OpenAI API key |
| `GITHUB_WEBHOOK_SECRET` | Shared secret used to verify that webhook requests really come from GitHub |

Docker Compose sets `DATABASE_URL` for the bundled PostgreSQL container. The credentials in `docker-compose.yml` are for local development only; don't reuse them anywhere else.

## Webhook setup
1. In the target repository, go to **Settings → Webhooks → Add webhook**.
2. **Payload URL:** your service's public URL plus the webhook path (use a tunnel such as ngrok for local testing).
3. **Content type:** `application/json`.
4. **Secret:** the same value as `GITHUB_WEBHOOK_SECRET`. Generate one with `openssl rand -hex 32`.
5. **Events:** select *Pull requests*.

## Security
- **Webhook signatures are verified.** GitHub signs each delivery with HMAC-SHA256 over the raw request body and sends it in `X-Hub-Signature-256`. The service recomputes the signature with `GITHUB_WEBHOOK_SECRET` and compares it in constant time (`hmac.compare_digest`). Invalid or missing signatures get `401`.
- **Fails closed.** If `GITHUB_WEBHOOK_SECRET` is not set, every webhook request is rejected (`500`) instead of being accepted unauthenticated.
- **Why it matters:** without this check, anyone who finds the endpoint could trigger OpenAI calls (cost) and post comments on pull requests.
- Secrets come from environment variables. `.env` is git-ignored; `.env.example` contains placeholders only.

Test a signed request by hand:
```bash
BODY='{"action":"opened"}'
SIG="sha256=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$GITHUB_WEBHOOK_SECRET" | sed 's/^.* //')"
curl -i -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" -H "X-Hub-Signature-256: $SIG" -d "$BODY"
```

## Testing
```bash
pip install -r requirements-dev.txt
pytest -q
```
The signature tests cover a valid signature, a tampered body, a missing header, a wrong secret, a malformed header, the fail-closed case, and GitHub's published test vector.

## Limitations
- Reviews come from an LLM and can be wrong or miss problems. Treat them as suggestions.
- Each review sends code to the OpenAI API, so don't use it on private or employer code.
