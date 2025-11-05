from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import Review
from .github import get_pr_files, post_pr_comment
from .reviewer import review_code_with_llm
from .rate_limit import check_rate_limit
from .language_utils import detect_language, generate_language_prompt
import asyncio

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.post("/webhook/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    action = payload.get("action")

    if action not in ["opened", "synchronize"]:
        return {"status": "ignored"}

    pr_number = payload["pull_request"]["number"]
    repo_full_name = payload["repository"]["full_name"]
    branch = payload["pull_request"]["head"]["ref"]

    # Rate limit
    try:
        check_rate_limit(repo_full_name)
    except Exception as e:
        return {"status": "rate_limited", "message": str(e)}

    # Fetch PR files
    files = await get_pr_files(repo_full_name, pr_number)
    code_reviews = []

    for f in files:
        filename = f["filename"]
        if f["status"] == "removed":
            continue

        language = detect_language(filename)
        if language == "unknown":
            continue

        patch = f.get("patch")
        if not patch:
            continue

        # Generate language-aware prompt
        prompt = generate_language_prompt(language, patch)

        # Send prompt to OpenAI for review
        review_text = review_code_with_llm(prompt)

        code_reviews.append({
            "file": filename,
            "language": language,
            "comments": review_text
        })

    if not code_reviews:
        return {"status": "no_supported_files"}

    # Save to DB
    review_entry = Review(
        repo=repo_full_name,
        pr_number=pr_number,
        branch=branch,
        status="completed",
        review={"comments": code_reviews}
    )
    db.add(review_entry)
    db.commit()
    db.refresh(review_entry)

    # Post summary comment
    summary = "\n\n".join(
        [f"### {r['file']} ({r['language']})\n{r['comments']}" for r in code_reviews]
    )
    asyncio.create_task(post_pr_comment(repo_full_name, pr_number, summary))

    return {"status": "reviewed", "files_reviewed": len(code_reviews)}
