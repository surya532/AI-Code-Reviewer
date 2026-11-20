# AI Code Reviewer

An automated code review service that integrates with GitHub to review pull requests using OpenAI GPT models.  
It provides suggestions for code optimizations, detects missing tests, and identifies security risks.

## Features

- Automatic code review on pull requests
- Python code focused (can be extended)
- Detects performance issues, security risks, and missing tests
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
Set these in `.env`:

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | Token allowed to read pull requests and post comments |
| `OPENAI_API_KEY` | OpenAI API key |

Docker Compose sets `DATABASE_URL` for the bundled PostgreSQL container. The credentials in `docker-compose.yml` are for local development only; don't reuse them anywhere else.
