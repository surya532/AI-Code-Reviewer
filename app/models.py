from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP
from sqlalchemy.sql import func
from .db import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    repo = Column(String, index=True)
    pr_number = Column(Integer, index=True)
    branch = Column(String)
    status = Column(String, default="pending")
    review = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
