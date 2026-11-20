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

```bash
git clone https://github.com/surya532/AI-Code-Reviewer.git
cd AI-Code-Reviewer
cp .env.example .env        # then fill in the values below
docker compose up --build
```

### Configuration
| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `GITHUB_TOKEN` | Token allowed to read PRs and post comments |
| `DATABASE_URL` | PostgreSQL connection string |
