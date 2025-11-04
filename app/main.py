from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import Review
from .github import get_pr_files, post_pr_comment
from .reviewer import review_code_with_llm
from .rate_limit import check_rate_limit
import asyncio

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.post("/webhook/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    action = payload.get("action")
    
    # Only handle PR opened or updated
    if action not in ["opened", "synchronize"]:
        return {"status": "ignored"}

    pr_number = payload["pull_request"]["number"]
    repo_full_name = payload["repository"]["full_name"]
    branch = payload["pull_request"]["head"]["ref"]

    # ---------------------------
    # Rate-limiting check
    # ---------------------------
    try:
        check_rate_limit(repo_full_name)
    except Exception as e:
        return {"status": "rate_limited", "message": str(e)}

    # ---------------------------
    # Fetch changed files from PR
    # ---------------------------
    files = await get_pr_files(repo_full_name, pr_number)
    code_snippets = []

    for f in files:
        if f["filename"].endswith(".py") and f["status"] != "removed":
            patch = f.get("patch")
            if patch:
                code_snippets.append(f"# File: {f['filename']}\n{patch}")

    if not code_snippets:
        return {"status": "no python files"}

    # ---------------------------
    # Review code using LLM
    # ---------------------------
    review_text = review_code_with_llm(code_snippets)

    # ---------------------------
    # Save review to DB
    # ---------------------------
    review_entry = Review(
        repo=repo_full_name,
        pr_number=pr_number,
        branch=branch,
        status="completed",
        review={"comments": review_text}
    )
    db.add(review_entry)
    db.commit()
    db.refresh(review_entry)

    # ---------------------------
    # Post review comment to GitHub
    # ---------------------------
    asyncio.create_task(post_pr_comment(repo_full_name, pr_number, review_text))

    return {"status": "reviewed"}
