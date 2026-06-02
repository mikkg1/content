from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import SCHEMA, AuditMixin, Base, new_uuid

if TYPE_CHECKING:
    from .club import Club
    from .contact import Contact


class Phone(AuditMixin, Base):
    __tablename__ = "phones"
    __table_args__ = (
        CheckConstraint(
            r"number_e164 ~ '^\+[1-9]\d{6,14}$'",
            name="e164_format",
        ),
        CheckConstraint(
            "type IN ('mobile', 'office', 'fax')",
            name="phone_type_enum",
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

    number_e164: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False, default="office")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    club: Mapped[Optional["Club"]] = relationship(
        "Club",
        foreign_keys=[club_id],
        back_populates="phones",
    )
    contact: Mapped[Optional["Contact"]] = relationship(
        "Contact",
        foreign_keys=[contact_id],
        back_populates="phones",
    )

    def __repr__(self) -> str:
        return f"<Phone id={self.id} number={self.number_e164!r} type={self.type!r}>"
