from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import SCHEMA, AuditMixin, Base, new_uuid

if TYPE_CHECKING:
    from .club import Club
    from .contact import Contact

_PLATFORMS = ("twitter", "instagram", "facebook", "linkedin", "youtube", "tiktok", "other")


class SocialProfile(AuditMixin, Base):
    __tablename__ = "social_profiles"
    __table_args__ = (
        CheckConstraint(
            "platform IN ('twitter','instagram','facebook','linkedin','youtube','tiktok','other')",
            name="platform_enum",
        ),
        CheckConstraint(
            "(club_id IS NOT NULL)::INT + (contact_id IS NOT NULL)::INT >= 1",
            name="owner_required",
        ),
        CheckConstraint(
            "followers_count >= 0",
            name="followers_nonneg",
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

    platform: Mapped[str] = mapped_column(Text, nullable=False)
    handle: Mapped[Optional[str]] = mapped_column(Text)
    profile_url: Mapped[Optional[str]] = mapped_column(Text)
    followers_count: Mapped[Optional[int]] = mapped_column(Integer)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    club: Mapped[Optional["Club"]] = relationship(
        "Club",
        foreign_keys=[club_id],
        back_populates="social_profiles",
    )
    contact: Mapped[Optional["Contact"]] = relationship(
        "Contact",
        foreign_keys=[contact_id],
        back_populates="social_profiles",
    )

    def __repr__(self) -> str:
        return f"<SocialProfile id={self.id} platform={self.platform!r} handle={self.handle!r}>"
