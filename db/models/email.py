from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import SCHEMA, AuditMixin, Base, new_uuid

if TYPE_CHECKING:
    from .club import Club
    from .contact import Contact

_EMAIL_TYPES = ("primary", "general", "billing")


class Email(AuditMixin, Base):
    __tablename__ = "emails"
    __table_args__ = (
        CheckConstraint(
            "type IN ('primary', 'general', 'billing')",
            name="email_type_enum",
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

    address: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False, default="general")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    mx_valid: Mapped[Optional[bool]] = mapped_column(Boolean)

    # Relationships
    club: Mapped[Optional["Club"]] = relationship(
        "Club",
        foreign_keys=[club_id],
        back_populates="emails",
    )
    contact: Mapped[Optional["Contact"]] = relationship(
        "Contact",
        foreign_keys=[contact_id],
        back_populates="emails",
    )

    def __repr__(self) -> str:
        return f"<Email id={self.id} address={self.address!r} verified={self.is_verified}>"
