import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Review
from .github import get_pr_files, post_pr_comment
from .reviewer import review_code_with_llm
from .rate_limit import check_rate_limit, RateLimitExceeded, RateLimiterUnavailable
from .language_utils import detect_language, generate_language_prompt
from .security import require_github_signature

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are created at startup, not at import, so importing this module (e.g. in tests) needs no database.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/webhook/github", dependencies=[Depends(require_github_signature)])
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    action = payload.get("action")

    if action not in ["opened", "synchronize"]:
        return {"status": "ignored"}

    pr_number = payload["pull_request"]["number"]
    repo_full_name = payload["repository"]["full_name"]
    branch = payload["pull_request"]["head"]["ref"]
    head_sha = payload["pull_request"]["head"]["sha"]

    # Already reviewed and commented for this exact commit? Do nothing (saves OpenAI cost, avoids duplicate comments).
    review_entry = (
        db.query(Review)
        .filter_by(repo=repo_full_name, pr_number=pr_number, head_sha=head_sha)
        .first()
    )
    if review_entry and review_entry.status == "completed":
        return {"status": "duplicate", "review_id": review_entry.id}

    # Rate limit
    try:
        check_rate_limit(repo_full_name)
    except RateLimitExceeded as e:
        return JSONResponse(status_code=429, content={"status": "rate_limited", "message": str(e)})
    except RateLimiterUnavailable:
        # Fail closed: every review costs money, so do not review without a working limiter.
        logger.exception("Rate limiter unavailable; not reviewing %s#%s", repo_full_name, pr_number)
        return JSONResponse(status_code=503, content={"status": "rate_limiter_unavailable"})

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

        prompt = generate_language_prompt(language, patch)
        review_text = await review_code_with_llm(prompt)

        code_reviews.append({
            "file": filename,
            "language": language,
            "comments": review_text,
        })

    if not code_reviews:
        return {"status": "no_supported_files"}

    # Save the review (or reuse the row from an earlier attempt whose comment failed to post)
    if review_entry is None:
        review_entry = Review(
            repo=repo_full_name,
            pr_number=pr_number,
            head_sha=head_sha,
            branch=branch,
            status="reviewed",
            review={"comments": code_reviews},
        )
        db.add(review_entry)
    else:
        review_entry.review = {"comments": code_reviews}
        review_entry.status = "reviewed"

    try:
        db.commit()
    except IntegrityError:
        # A concurrent delivery for the same commit won the race.
        db.rollback()
        return {"status": "duplicate"}
    db.refresh(review_entry)

    # Post summary comment; only mark the review completed once GitHub accepted it
    summary = "\n\n".join(
        [f"### {r['file']} ({r['language']})\n{r['comments']}" for r in code_reviews]
    )
    try:
        await post_pr_comment(repo_full_name, pr_number, summary)
    except Exception:
        logger.exception("Failed to post PR comment for %s#%s", repo_full_name, pr_number)
        review_entry.status = "post_failed"
        db.commit()
        return {"status": "post_failed", "review_id": review_entry.id}

    review_entry.status = "completed"
    db.commit()
    return {"status": "reviewed", "files_reviewed": len(code_reviews)}
