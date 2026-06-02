from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import SCHEMA, Base, new_uuid

if TYPE_CHECKING:
    from .club import Club
    from .contact import Contact

_PROVIDERS = ("clearbit", "hunter", "fullcontact", "apollo", "manual", "other")


class EnrichmentData(Base):
    """Stores raw provider responses; no soft-delete — append new rows on re-fetch."""

    __tablename__ = "enrichment_data"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('clearbit','hunter','fullcontact','apollo','manual','other')",
            name="provider_enum",
        ),
        CheckConstraint(
            "(club_id IS NOT NULL)::INT + (contact_id IS NOT NULL)::INT >= 1",
            name="owner_required",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=new_uuid,
    )
    club_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.clubs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.contacts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    provider: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate="now()", nullable=False
    )

    # Relationships
    club: Mapped[Optional["Club"]] = relationship(
        "Club",
        foreign_keys=[club_id],
        back_populates="enrichment_data",
    )
    contact: Mapped[Optional["Contact"]] = relationship(
        "Contact",
        foreign_keys=[contact_id],
        back_populates="enrichment_data",
    )

    def __repr__(self) -> str:
        return f"<EnrichmentData id={self.id} provider={self.provider!r}>"
