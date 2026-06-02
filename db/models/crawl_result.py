from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import SCHEMA, Base, new_uuid

if TYPE_CHECKING:
    from .club import Club
    from .crawl_job import CrawlJob

_EXTRACT_STATUSES = ("pending", "extracted", "failed", "skipped")


class CrawlResult(Base):
    """No soft-delete — crawl results are append-only raw records."""

    __tablename__ = "crawl_results"
    __table_args__ = (
        CheckConstraint(
            "extract_status IN ('pending', 'extracted', 'failed', 'skipped')",
            name="extract_status_enum",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=new_uuid,
    )
    crawl_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.crawl_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Set after extraction links the raw page to a known club
    club_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.clubs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_fingerprint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer)
    content_type: Mapped[Optional[str]] = mapped_column(Text)
    s3_key: Mapped[Optional[str]] = mapped_column(Text)

    extract_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending", index=True
    )
    extracted_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate="now()", nullable=False
    )

    # Relationships
    crawl_job: Mapped["CrawlJob"] = relationship("CrawlJob", back_populates="results")
    club: Mapped[Optional["Club"]] = relationship("Club", back_populates="crawl_results")

    def __repr__(self) -> str:
        return (
            f"<CrawlResult id={self.id} url={self.url!r} "
            f"extract_status={self.extract_status!r}>"
        )
