"""Initial schema — soccer_leads

Revision ID: 0001
Revises:
Create Date: 2026-06-02
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "soccer_leads"


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Extensions & schema
    # -------------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    # -------------------------------------------------------------------------
    # updated_at trigger function (shared by all tables)
    # -------------------------------------------------------------------------
    op.execute(f"""
        CREATE OR REPLACE FUNCTION {SCHEMA}.set_updated_at()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$
    """)

    # -------------------------------------------------------------------------
    # clubs
    # -------------------------------------------------------------------------
    op.create_table(
        "clubs",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name",             sa.Text,    nullable=False),
        sa.Column("slug",             sa.Text,    nullable=False),
        sa.Column("website_url",      sa.Text),
        sa.Column("description",      sa.Text),
        sa.Column("division",         sa.Text),
        sa.Column("league_affiliation", sa.Text),
        sa.Column("founded_year",     sa.Integer),
        sa.Column("member_count_est", sa.Integer),
        sa.Column("team_count_est",   sa.Integer),
        sa.Column("age_groups",       postgresql.ARRAY(sa.Text), nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column("program_types",    postgresql.ARRAY(sa.Text), nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column("street_address",   sa.Text),
        sa.Column("city",             sa.Text),
        sa.Column("state_code",       sa.String(2)),
        sa.Column("zip_code",         sa.Text),
        sa.Column("country_code",     sa.String(2), nullable=False,
                  server_default=sa.text("'US'")),
        sa.Column("latitude",         sa.Float),
        sa.Column("longitude",        sa.Float),
        sa.Column("data_source",      sa.Text),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",       sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",       sa.DateTime(timezone=True)),
        sa.CheckConstraint("founded_year > 1850 AND founded_year < 2100",
                           name="clubs_founded_year_range_check"),
        sa.CheckConstraint("member_count_est >= 0",  name="clubs_member_count_nonneg_check"),
        sa.CheckConstraint("team_count_est >= 0",    name="clubs_team_count_nonneg_check"),
        sa.CheckConstraint(r"state_code ~ '^[A-Z]{2}$'", name="clubs_state_code_format_check"),
        sa.CheckConstraint("latitude  BETWEEN -90  AND 90",  name="clubs_latitude_range_check"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="clubs_longitude_range_check"),
        sa.UniqueConstraint("slug", name="clubs_slug_key"),
        schema=SCHEMA,
    )
    op.create_index("clubs_slug_uidx",          SCHEMA + ".clubs", ["slug"],   unique=True,
                    schema=SCHEMA)
    op.create_index("clubs_state_division_idx", SCHEMA + ".clubs",
                    ["state_code", "division"],  schema=SCHEMA)
    op.create_index("clubs_updated_at_idx",     SCHEMA + ".clubs",
                    [sa.text("updated_at DESC")], schema=SCHEMA)
    # Partial index for active clubs
    op.execute(f"""
        CREATE INDEX clubs_active_idx
            ON {SCHEMA}.clubs (id)
            WHERE deleted_at IS NULL
    """)
    # Trigram index for fuzzy name search
    op.execute(f"""
        CREATE INDEX clubs_name_trgm_idx
            ON {SCHEMA}.clubs USING GIN (name gin_trgm_ops)
    """)
    op.execute(f"""
        CREATE INDEX clubs_age_groups_gin_idx
            ON {SCHEMA}.clubs USING GIN (age_groups)
    """)
    op.execute(f"""
        CREATE INDEX clubs_program_types_gin_idx
            ON {SCHEMA}.clubs USING GIN (program_types)
    """)
    op.execute(f"""
        CREATE TRIGGER clubs_updated_at
            BEFORE UPDATE ON {SCHEMA}.clubs
            FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.set_updated_at()
    """)

    # -------------------------------------------------------------------------
    # contacts
    # -------------------------------------------------------------------------
    op.create_table(
        "contacts",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("club_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.Text),
        sa.Column("last_name",  sa.Text),
        sa.Column("role",       sa.Text),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["club_id"], [f"{SCHEMA}.clubs.id"],
                                ondelete="CASCADE", name="contacts_club_id_fkey"),
        schema=SCHEMA,
    )
    op.create_index("contacts_club_id_idx",      SCHEMA + ".contacts", ["club_id"],
                    schema=SCHEMA)
    op.create_index("contacts_club_primary_idx", SCHEMA + ".contacts",
                    ["club_id", "is_primary"], schema=SCHEMA)
    op.execute(f"""
        CREATE INDEX contacts_active_idx
            ON {SCHEMA}.contacts (id)
            WHERE deleted_at IS NULL
    """)
    op.execute(f"""
        CREATE TRIGGER contacts_updated_at
            BEFORE UPDATE ON {SCHEMA}.contacts
            FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.set_updated_at()
    """)

    # -------------------------------------------------------------------------
    # emails
    # -------------------------------------------------------------------------
    op.create_table(
        "emails",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("club_id",     postgresql.UUID(as_uuid=True)),
        sa.Column("contact_id",  postgresql.UUID(as_uuid=True)),
        sa.Column("address",     sa.Text, nullable=False),
        sa.Column("type",        sa.Text, nullable=False, server_default=sa.text("'general'")),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("mx_valid",    sa.Boolean),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",  sa.DateTime(timezone=True)),
        sa.CheckConstraint("type IN ('primary', 'general', 'billing')",
                           name="emails_email_type_enum_check"),
        sa.CheckConstraint(
            "(club_id IS NOT NULL)::INT + (contact_id IS NOT NULL)::INT >= 1",
            name="emails_owner_required_check",
        ),
        sa.ForeignKeyConstraint(["club_id"],    [f"{SCHEMA}.clubs.id"],
                                ondelete="CASCADE", name="emails_club_id_fkey"),
        sa.ForeignKeyConstraint(["contact_id"], [f"{SCHEMA}.contacts.id"],
                                ondelete="CASCADE", name="emails_contact_id_fkey"),
        schema=SCHEMA,
    )
    op.execute(f"""
        CREATE INDEX emails_club_id_idx ON {SCHEMA}.emails (club_id)
            WHERE club_id IS NOT NULL
    """)
    op.execute(f"""
        CREATE INDEX emails_contact_id_idx ON {SCHEMA}.emails (contact_id)
            WHERE contact_id IS NOT NULL
    """)
    op.execute(f"""
        CREATE INDEX emails_active_idx ON {SCHEMA}.emails (id)
            WHERE deleted_at IS NULL
    """)
    op.execute(f"""
        CREATE UNIQUE INDEX emails_club_address_uidx
            ON {SCHEMA}.emails (club_id, lower(address))
            WHERE club_id IS NOT NULL AND deleted_at IS NULL
    """)
    op.execute(f"""
        CREATE UNIQUE INDEX emails_contact_address_uidx
            ON {SCHEMA}.emails (contact_id, lower(address))
            WHERE contact_id IS NOT NULL AND deleted_at IS NULL
    """)
    op.execute(f"""
        CREATE TRIGGER emails_updated_at
            BEFORE UPDATE ON {SCHEMA}.emails
            FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.set_updated_at()
    """)

    # -------------------------------------------------------------------------
    # phones
    # -------------------------------------------------------------------------
    op.create_table(
        "phones",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("club_id",     postgresql.UUID(as_uuid=True)),
        sa.Column("contact_id",  postgresql.UUID(as_uuid=True)),
        sa.Column("number_e164", sa.Text, nullable=False),
        sa.Column("type",        sa.Text, nullable=False, server_default=sa.text("'office'")),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",  sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            r"number_e164 ~ '^\+[1-9]\d{6,14}$'", name="phones_e164_format_check"
        ),
        sa.CheckConstraint(
            "type IN ('mobile', 'office', 'fax')", name="phones_phone_type_enum_check"
        ),
        sa.CheckConstraint(
            "(club_id IS NOT NULL)::INT + (contact_id IS NOT NULL)::INT >= 1",
            name="phones_owner_required_check",
        ),
        sa.ForeignKeyConstraint(["club_id"],    [f"{SCHEMA}.clubs.id"],
                                ondelete="CASCADE", name="phones_club_id_fkey"),
        sa.ForeignKeyConstraint(["contact_id"], [f"{SCHEMA}.contacts.id"],
                                ondelete="CASCADE", name="phones_contact_id_fkey"),
        schema=SCHEMA,
    )
    op.create_index("phones_number_idx",     SCHEMA + ".phones", ["number_e164"], schema=SCHEMA)
    op.execute(f"""
        CREATE INDEX phones_club_id_idx    ON {SCHEMA}.phones (club_id)
            WHERE club_id IS NOT NULL
    """)
    op.execute(f"""
        CREATE INDEX phones_contact_id_idx ON {SCHEMA}.phones (contact_id)
            WHERE contact_id IS NOT NULL
    """)
    op.execute(f"""
        CREATE INDEX phones_active_idx ON {SCHEMA}.phones (id)
            WHERE deleted_at IS NULL
    """)
    op.execute(f"""
        CREATE TRIGGER phones_updated_at
            BEFORE UPDATE ON {SCHEMA}.phones
            FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.set_updated_at()
    """)

    # -------------------------------------------------------------------------
    # social_profiles
    # -------------------------------------------------------------------------
    op.create_table(
        "social_profiles",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("club_id",         postgresql.UUID(as_uuid=True)),
        sa.Column("contact_id",      postgresql.UUID(as_uuid=True)),
        sa.Column("platform",        sa.Text, nullable=False),
        sa.Column("handle",          sa.Text),
        sa.Column("profile_url",     sa.Text),
        sa.Column("followers_count", sa.Integer),
        sa.Column("is_verified",     sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",      sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",      sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "platform IN ('twitter','instagram','facebook','linkedin','youtube','tiktok','other')",
            name="social_profiles_platform_enum_check",
        ),
        sa.CheckConstraint(
            "(club_id IS NOT NULL)::INT + (contact_id IS NOT NULL)::INT >= 1",
            name="social_profiles_owner_required_check",
        ),
        sa.CheckConstraint("followers_count >= 0", name="social_profiles_followers_nonneg_check"),
        sa.ForeignKeyConstraint(["club_id"],    [f"{SCHEMA}.clubs.id"],
                                ondelete="CASCADE", name="social_profiles_club_id_fkey"),
        sa.ForeignKeyConstraint(["contact_id"], [f"{SCHEMA}.contacts.id"],
                                ondelete="CASCADE", name="social_profiles_contact_id_fkey"),
        schema=SCHEMA,
    )
    op.create_index("social_profiles_platform_handle_idx", SCHEMA + ".social_profiles",
                    ["platform", "handle"], schema=SCHEMA)
    op.execute(f"""
        CREATE INDEX social_profiles_club_id_idx ON {SCHEMA}.social_profiles (club_id)
            WHERE club_id IS NOT NULL
    """)
    op.execute(f"""
        CREATE INDEX social_profiles_contact_id_idx ON {SCHEMA}.social_profiles (contact_id)
            WHERE contact_id IS NOT NULL
    """)
    op.execute(f"""
        CREATE UNIQUE INDEX social_profiles_club_platform_uidx
            ON {SCHEMA}.social_profiles (club_id, platform)
            WHERE club_id IS NOT NULL AND deleted_at IS NULL
    """)
    op.execute(f"""
        CREATE UNIQUE INDEX social_profiles_contact_platform_uidx
            ON {SCHEMA}.social_profiles (contact_id, platform)
            WHERE contact_id IS NOT NULL AND deleted_at IS NULL
    """)
    op.execute(f"""
        CREATE TRIGGER social_profiles_updated_at
            BEFORE UPDATE ON {SCHEMA}.social_profiles
            FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.set_updated_at()
    """)

    # -------------------------------------------------------------------------
    # crawl_jobs
    # -------------------------------------------------------------------------
    op.create_table(
        "crawl_jobs",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("spider_name",   sa.Text, nullable=False),
        sa.Column("status",        sa.Text, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("config",        postgresql.JSONB, nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column("pages_crawled", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("pages_failed",  sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text),
        sa.Column("started_at",    sa.DateTime(timezone=True)),
        sa.Column("finished_at",   sa.DateTime(timezone=True)),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",    sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at",    sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('pending','running','done','failed')",
                           name="crawl_jobs_status_enum_check"),
        sa.CheckConstraint("pages_crawled >= 0", name="crawl_jobs_pages_crawled_nonneg_check"),
        sa.CheckConstraint("pages_failed  >= 0", name="crawl_jobs_pages_failed_nonneg_check"),
        schema=SCHEMA,
    )
    op.create_index("crawl_jobs_spider_status_idx", SCHEMA + ".crawl_jobs",
                    ["spider_name", "status"], schema=SCHEMA)
    op.create_index("crawl_jobs_status_idx",        SCHEMA + ".crawl_jobs",
                    ["status"], schema=SCHEMA)
    op.create_index("crawl_jobs_started_at_idx",    SCHEMA + ".crawl_jobs",
                    [sa.text("started_at DESC")], schema=SCHEMA)
    op.execute(f"""
        CREATE TRIGGER crawl_jobs_updated_at
            BEFORE UPDATE ON {SCHEMA}.crawl_jobs
            FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.set_updated_at()
    """)

    # -------------------------------------------------------------------------
    # crawl_results
    # -------------------------------------------------------------------------
    op.create_table(
        "crawl_results",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("crawl_job_id",     postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("club_id",          postgresql.UUID(as_uuid=True)),
        sa.Column("url",              sa.Text, nullable=False),
        sa.Column("url_fingerprint",  sa.Text, nullable=False),
        sa.Column("http_status",      sa.Integer),
        sa.Column("content_type",     sa.Text),
        sa.Column("s3_key",           sa.Text),
        sa.Column("extract_status",   sa.Text, nullable=False,
                  server_default=sa.text("'pending'")),
        sa.Column("extracted_data",   postgresql.JSONB),
        sa.Column("crawled_at",       sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",       sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "extract_status IN ('pending','extracted','failed','skipped')",
            name="crawl_results_extract_status_enum_check",
        ),
        sa.UniqueConstraint("url_fingerprint", name="crawl_results_url_fingerprint_key"),
        sa.ForeignKeyConstraint(["crawl_job_id"], [f"{SCHEMA}.crawl_jobs.id"],
                                ondelete="CASCADE", name="crawl_results_crawl_job_id_fkey"),
        sa.ForeignKeyConstraint(["club_id"],      [f"{SCHEMA}.clubs.id"],
                                ondelete="SET NULL", name="crawl_results_club_id_fkey"),
        schema=SCHEMA,
    )
    op.create_index("crawl_results_fingerprint_uidx",   SCHEMA + ".crawl_results",
                    ["url_fingerprint"], unique=True, schema=SCHEMA)
    op.create_index("crawl_results_crawl_job_idx",      SCHEMA + ".crawl_results",
                    ["crawl_job_id"],   schema=SCHEMA)
    op.create_index("crawl_results_extract_status_idx", SCHEMA + ".crawl_results",
                    ["extract_status"], schema=SCHEMA)
    op.execute(f"""
        CREATE INDEX crawl_results_club_id_idx ON {SCHEMA}.crawl_results (club_id)
            WHERE club_id IS NOT NULL
    """)
    op.create_index("crawl_results_crawled_at_idx", SCHEMA + ".crawl_results",
                    [sa.text("crawled_at DESC")], schema=SCHEMA)
    op.execute(f"""
        CREATE TRIGGER crawl_results_updated_at
            BEFORE UPDATE ON {SCHEMA}.crawl_results
            FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.set_updated_at()
    """)

    # -------------------------------------------------------------------------
    # enrichment_data
    # -------------------------------------------------------------------------
    op.create_table(
        "enrichment_data",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("club_id",     postgresql.UUID(as_uuid=True)),
        sa.Column("contact_id",  postgresql.UUID(as_uuid=True)),
        sa.Column("provider",    sa.Text, nullable=False),
        sa.Column("payload",     postgresql.JSONB, nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column("fetched_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "provider IN ('clearbit','hunter','fullcontact','apollo','manual','other')",
            name="enrichment_data_provider_enum_check",
        ),
        sa.CheckConstraint(
            "(club_id IS NOT NULL)::INT + (contact_id IS NOT NULL)::INT >= 1",
            name="enrichment_data_owner_required_check",
        ),
        sa.ForeignKeyConstraint(["club_id"],    [f"{SCHEMA}.clubs.id"],
                                ondelete="CASCADE", name="enrichment_data_club_id_fkey"),
        sa.ForeignKeyConstraint(["contact_id"], [f"{SCHEMA}.contacts.id"],
                                ondelete="CASCADE", name="enrichment_data_contact_id_fkey"),
        schema=SCHEMA,
    )
    op.execute(f"""
        CREATE INDEX enrichment_club_provider_idx
            ON {SCHEMA}.enrichment_data (club_id, provider)
            WHERE club_id IS NOT NULL
    """)
    op.execute(f"""
        CREATE INDEX enrichment_contact_provider_idx
            ON {SCHEMA}.enrichment_data (contact_id, provider)
            WHERE contact_id IS NOT NULL
    """)
    op.create_index("enrichment_fetched_at_idx", SCHEMA + ".enrichment_data",
                    [sa.text("fetched_at DESC")], schema=SCHEMA)
    op.execute(f"""
        CREATE TRIGGER enrichment_data_updated_at
            BEFORE UPDATE ON {SCHEMA}.enrichment_data
            FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.set_updated_at()
    """)

    # -------------------------------------------------------------------------
    # lead_scores
    # -------------------------------------------------------------------------
    op.create_table(
        "lead_scores",
        sa.Column("id",                 postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("club_id",            postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score",              sa.Float, nullable=False),
        sa.Column("tier",               sa.Text,  nullable=False),
        sa.Column("completeness_score", sa.Float),
        sa.Column("contact_score",      sa.Float),
        sa.Column("program_score",      sa.Float),
        sa.Column("member_score",       sa.Float),
        sa.Column("recency_score",      sa.Float),
        sa.Column("score_breakdown",    postgresql.JSONB, nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column("model_version",      sa.Text),
        sa.Column("scored_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_at",         sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",         sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="lead_scores_score_range_check"),
        sa.CheckConstraint("tier IN ('COLD','WARM','HOT')",  name="lead_scores_tier_enum_check"),
        sa.CheckConstraint("completeness_score BETWEEN 0 AND 100",
                           name="lead_scores_completeness_range_check"),
        sa.CheckConstraint("contact_score BETWEEN 0 AND 100",
                           name="lead_scores_contact_range_check"),
        sa.CheckConstraint("program_score BETWEEN 0 AND 100",
                           name="lead_scores_program_range_check"),
        sa.CheckConstraint("member_score  BETWEEN 0 AND 100",
                           name="lead_scores_member_range_check"),
        sa.CheckConstraint("recency_score BETWEEN 0 AND 100",
                           name="lead_scores_recency_range_check"),
        sa.UniqueConstraint("club_id", name="lead_scores_club_id_key"),
        sa.ForeignKeyConstraint(["club_id"], [f"{SCHEMA}.clubs.id"],
                                ondelete="CASCADE", name="lead_scores_club_id_fkey"),
        schema=SCHEMA,
    )
    op.create_index("lead_scores_club_uidx",     SCHEMA + ".lead_scores",
                    ["club_id"], unique=True, schema=SCHEMA)
    op.create_index("lead_scores_tier_score_idx", SCHEMA + ".lead_scores",
                    ["tier", sa.text("score DESC")], schema=SCHEMA)
    op.create_index("lead_scores_scored_at_idx",  SCHEMA + ".lead_scores",
                    [sa.text("scored_at DESC")], schema=SCHEMA)
    op.execute(f"""
        CREATE TRIGGER lead_scores_updated_at
            BEFORE UPDATE ON {SCHEMA}.lead_scores
            FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.set_updated_at()
    """)


def downgrade() -> None:
    SCHEMA = "soccer_leads"
    for table in [
        "lead_scores",
        "enrichment_data",
        "crawl_results",
        "crawl_jobs",
        "social_profiles",
        "phones",
        "emails",
        "contacts",
        "clubs",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{table} CASCADE")

    op.execute(f"DROP FUNCTION IF EXISTS {SCHEMA}.set_updated_at() CASCADE")
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
