from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func
from .db import Base


class Review(Base):
    __tablename__ = "reviews"
    # One review per repo + pull request + commit. This makes a redelivered webhook, or a double
    # trigger for the same commit, a no-op instead of a second review and a duplicate PR comment.
    __table_args__ = (UniqueConstraint("repo", "pr_number", "head_sha", name="uq_review_repo_pr_sha"),)

    id = Column(Integer, primary_key=True, index=True)
    repo = Column(String, index=True)
    pr_number = Column(Integer, index=True)
    head_sha = Column(String(40))
    branch = Column(String)
    status = Column(String, default="pending")
    review = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
