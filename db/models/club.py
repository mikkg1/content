from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, CheckConstraint, Float, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import SCHEMA, AuditMixin, Base, new_uuid

if TYPE_CHECKING:
    from .contact import Contact
    from .crawl_result import CrawlResult
    from .email import Email
    from .enrichment_data import EnrichmentData
    from .lead_score import LeadScore
    from .phone import Phone
    from .social_profile import SocialProfile


class Club(AuditMixin, Base):
    __tablename__ = "clubs"
    __table_args__ = (
        CheckConstraint(
            "founded_year > 1850 AND founded_year < 2100",
            name="founded_year_range",
        ),
        CheckConstraint(
            "member_count_est >= 0",
            name="member_count_nonneg",
        ),
        CheckConstraint(
            "team_count_est >= 0",
            name="team_count_nonneg",
        ),
        CheckConstraint(
            r"state_code ~ '^[A-Z]{2}$'",
            name="state_code_format",
        ),
        CheckConstraint(
            "latitude BETWEEN -90 AND 90",
            name="latitude_range",
        ),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name="longitude_range",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=new_uuid,
    )

    # Identity
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    website_url: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Classification
    division: Mapped[Optional[str]] = mapped_column(Text)
    league_affiliation: Mapped[Optional[str]] = mapped_column(Text)
    founded_year: Mapped[Optional[int]] = mapped_column(Integer)
    member_count_est: Mapped[Optional[int]] = mapped_column(Integer)
    team_count_est: Mapped[Optional[int]] = mapped_column(Integer)
    age_groups: Mapped[List[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    program_types: Mapped[List[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )

    # Location
    street_address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(Text)
    state_code: Mapped[Optional[str]] = mapped_column(Text)
    zip_code: Mapped[Optional[str]] = mapped_column(Text)
    country_code: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'US'"))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)

    # Lineage
    data_source: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    contacts: Mapped[List["Contact"]] = relationship(
        "Contact",
        back_populates="club",
        cascade="all, delete-orphan",
        lazy="select",
    )
    emails: Mapped[List["Email"]] = relationship(
        "Email",
        primaryjoin="and_(Email.club_id == Club.id, Email.deleted_at.is_(None))",
        back_populates="club",
        cascade="all, delete-orphan",
        lazy="select",
    )
    phones: Mapped[List["Phone"]] = relationship(
        "Phone",
        primaryjoin="and_(Phone.club_id == Club.id, Phone.deleted_at.is_(None))",
        back_populates="club",
        cascade="all, delete-orphan",
        lazy="select",
    )
    social_profiles: Mapped[List["SocialProfile"]] = relationship(
        "SocialProfile",
        primaryjoin="and_(SocialProfile.club_id == Club.id, SocialProfile.deleted_at.is_(None))",
        back_populates="club",
        cascade="all, delete-orphan",
        lazy="select",
    )
    crawl_results: Mapped[List["CrawlResult"]] = relationship(
        "CrawlResult",
        back_populates="club",
        lazy="select",
    )
    enrichment_data: Mapped[List["EnrichmentData"]] = relationship(
        "EnrichmentData",
        primaryjoin="EnrichmentData.club_id == Club.id",
        back_populates="club",
        cascade="all, delete-orphan",
        lazy="select",
    )
    lead_score: Mapped[Optional["LeadScore"]] = relationship(
        "LeadScore",
        back_populates="club",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Club id={self.id} name={self.name!r} tier={self.lead_score.tier if self.lead_score else None!r}>"
