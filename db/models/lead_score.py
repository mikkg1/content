from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import SCHEMA, Base, new_uuid

if TYPE_CHECKING:
    from .club import Club

_TIERS = ("COLD", "WARM", "HOT")


class LeadScore(Base):
    """One score record per club. Re-scored in-place (UPDATE) rather than versioned rows."""

    __tablename__ = "lead_scores"
    __table_args__ = (
        CheckConstraint("score BETWEEN 0 AND 100", name="score_range"),
        CheckConstraint("tier IN ('COLD', 'WARM', 'HOT')", name="tier_enum"),
        CheckConstraint(
            "completeness_score BETWEEN 0 AND 100", name="completeness_range"
        ),
        CheckConstraint("contact_score BETWEEN 0 AND 100", name="contact_range"),
        CheckConstraint("program_score BETWEEN 0 AND 100", name="program_range"),
        CheckConstraint("member_score  BETWEEN 0 AND 100", name="member_range"),
        CheckConstraint("recency_score BETWEEN 0 AND 100", name="recency_range"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=new_uuid,
    )
    # One score per club — enforced by DB UNIQUE constraint
    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.clubs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    score: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    # Dimensional scores (feed into score_breakdown for explainability)
    completeness_score: Mapped[Optional[float]] = mapped_column(Float)
    contact_score: Mapped[Optional[float]] = mapped_column(Float)
    program_score: Mapped[Optional[float]] = mapped_column(Float)
    member_score: Mapped[Optional[float]] = mapped_column(Float)
    recency_score: Mapped[Optional[float]] = mapped_column(Float)

    score_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    model_version: Mapped[Optional[str]] = mapped_column(Text)

    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate="now()", nullable=False
    )

    # Relationships
    club: Mapped["Club"] = relationship("Club", back_populates="lead_score")

    @classmethod
    def tier_from_score(cls, score: float) -> str:
        if score >= 75:
            return "HOT"
        if score >= 40:
            return "WARM"
        return "COLD"

    def __repr__(self) -> str:
        return f"<LeadScore club_id={self.club_id} score={self.score:.1f} tier={self.tier!r}>"
