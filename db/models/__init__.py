"""SQLAlchemy models for the soccer_leads schema."""

from .base import SCHEMA, AuditMixin, Base
from .club import Club
from .contact import Contact
from .crawl_job import CrawlJob
from .crawl_result import CrawlResult
from .email import Email
from .enrichment_data import EnrichmentData
from .lead_score import LeadScore
from .phone import Phone
from .social_profile import SocialProfile

__all__ = [
    "SCHEMA",
    "AuditMixin",
    "Base",
    "Club",
    "Contact",
    "CrawlJob",
    "CrawlResult",
    "Email",
    "EnrichmentData",
    "LeadScore",
    "Phone",
    "SocialProfile",
]
