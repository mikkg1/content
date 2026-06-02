from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import CheckConstraint, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import SCHEMA, AuditMixin, Base, new_uuid

if TYPE_CHECKING:
    from .crawl_result import CrawlResult

_STATUSES = ("pending", "running", "done", "failed")


class CrawlJob(AuditMixin, Base):
    __tablename__ = "crawl_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'done', 'failed')",
            name="status_enum",
        ),
        CheckConstraint("pages_crawled >= 0", name="pages_crawled_nonneg"),
        CheckConstraint("pages_failed  >= 0", name="pages_failed_nonneg"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=new_uuid,
    )

    spider_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending", index=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    pages_crawled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    results: Mapped[List["CrawlResult"]] = relationship(
        "CrawlResult",
        back_populates="crawl_job",
        cascade="all, delete-orphan",
        lazy="select",
    )

    @property
    def success_rate(self) -> Optional[float]:
        total = self.pages_crawled + self.pages_failed
        if total == 0:
            return None
        return self.pages_crawled / total

    def __repr__(self) -> str:
        return f"<CrawlJob id={self.id} spider={self.spider_name!r} status={self.status!r}>"
