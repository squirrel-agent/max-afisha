from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    max_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    preferences: Mapped["UserPreference | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    categories: Mapped[list] = mapped_column(JSON, default=list)
    genres: Mapped[list] = mapped_column(JSON, default=list)
    budget_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_period: Mapped[str | None] = mapped_column(String(32), nullable=True)
    company: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Normalized questionnaire answers.  The *_text fields retain the user's
    # original free-form answer for embedding/context without using it as a SQL
    # filter.
    when: Mapped[str | None] = mapped_column(String(32), nullable=True)
    when_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(32), nullable=True)
    company_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    vibe: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vibe_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    questionnaire_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    novelty_preference: Mapped[float] = mapped_column(Float, default=0.5)
    profile_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="preferences")
