from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import SCHEMA, AuditMixin, Base, new_uuid

if TYPE_CHECKING:
    from .club import Club
    from .email import Email
    from .enrichment_data import EnrichmentData
    from .phone import Phone
    from .social_profile import SocialProfile


class Contact(AuditMixin, Base):
    __tablename__ = "contacts"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=new_uuid,
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.clubs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    first_name: Mapped[Optional[str]] = mapped_column(Text)
    last_name: Mapped[Optional[str]] = mapped_column(Text)
    role: Mapped[Optional[str]] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    club: Mapped["Club"] = relationship("Club", back_populates="contacts")
    emails: Mapped[List["Email"]] = relationship(
        "Email",
        primaryjoin="and_(Email.contact_id == Contact.id, Email.deleted_at.is_(None))",
        back_populates="contact",
        cascade="all, delete-orphan",
        lazy="select",
    )
    phones: Mapped[List["Phone"]] = relationship(
        "Phone",
        primaryjoin="and_(Phone.contact_id == Contact.id, Phone.deleted_at.is_(None))",
        back_populates="contact",
        cascade="all, delete-orphan",
        lazy="select",
    )
    social_profiles: Mapped[List["SocialProfile"]] = relationship(
        "SocialProfile",
        primaryjoin="and_(SocialProfile.contact_id == Contact.id, SocialProfile.deleted_at.is_(None))",
        back_populates="contact",
        cascade="all, delete-orphan",
        lazy="select",
    )
    enrichment_data: Mapped[List["EnrichmentData"]] = relationship(
        "EnrichmentData",
        primaryjoin="EnrichmentData.contact_id == Contact.id",
        back_populates="contact",
        cascade="all, delete-orphan",
        lazy="select",
    )

    @property
    def full_name(self) -> str:
        parts = filter(None, [self.first_name, self.last_name])
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"<Contact id={self.id} name={self.full_name!r} role={self.role!r}>"
