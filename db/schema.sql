-- =============================================================================
-- Soccer Club Lead Generation Platform — PostgreSQL Schema
-- Schema: soccer_leads
-- PostgreSQL 16+
-- Extensions: pgcrypto, pg_trgm
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA IF NOT EXISTS soccer_leads;

-- =============================================================================
-- ENUM-LIKE CHECK DOMAINS
-- =============================================================================

-- Defined inline on columns for auditability; swap to CREATE TYPE if preferred.

-- =============================================================================
-- clubs
-- =============================================================================

CREATE TABLE soccer_leads.clubs (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    name             TEXT        NOT NULL,
    slug             TEXT        NOT NULL,
    website_url      TEXT,
    description      TEXT,

    -- Classification
    division         TEXT,
    league_affiliation TEXT,
    founded_year     INT         CHECK (founded_year > 1850 AND founded_year < 2100),
    member_count_est INT         CHECK (member_count_est >= 0),
    team_count_est   INT         CHECK (team_count_est >= 0),
    age_groups       TEXT[]      NOT NULL DEFAULT '{}',
    program_types    TEXT[]      NOT NULL DEFAULT '{}',

    -- Location
    street_address   TEXT,
    city             TEXT,
    state_code       CHAR(2)     CHECK (state_code ~ '^[A-Z]{2}$'),
    zip_code         TEXT,
    country_code     CHAR(2)     NOT NULL DEFAULT 'US',
    latitude         FLOAT       CHECK (latitude  BETWEEN -90  AND 90),
    longitude        FLOAT       CHECK (longitude BETWEEN -180 AND 180),

    -- Lineage
    data_source      TEXT,

    -- Audit
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ,

    CONSTRAINT clubs_slug_key UNIQUE (slug)
);

-- Indexes
CREATE UNIQUE INDEX clubs_slug_uidx        ON soccer_leads.clubs (slug);
CREATE INDEX clubs_state_division_idx      ON soccer_leads.clubs (state_code, division);
CREATE INDEX clubs_active_idx              ON soccer_leads.clubs (id) WHERE deleted_at IS NULL;
CREATE INDEX clubs_name_trgm_idx           ON soccer_leads.clubs USING GIN (name gin_trgm_ops);
CREATE INDEX clubs_age_groups_gin_idx      ON soccer_leads.clubs USING GIN (age_groups);
CREATE INDEX clubs_program_types_gin_idx   ON soccer_leads.clubs USING GIN (program_types);
CREATE INDEX clubs_updated_at_idx          ON soccer_leads.clubs (updated_at DESC);

-- updated_at trigger (reused by all tables)
CREATE OR REPLACE FUNCTION soccer_leads.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER clubs_updated_at
    BEFORE UPDATE ON soccer_leads.clubs
    FOR EACH ROW EXECUTE FUNCTION soccer_leads.set_updated_at();

-- =============================================================================
-- contacts
-- =============================================================================

CREATE TABLE soccer_leads.contacts (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id          UUID        NOT NULL REFERENCES soccer_leads.clubs (id) ON DELETE CASCADE,

    first_name       TEXT,
    last_name        TEXT,
    role             TEXT,
    is_primary       BOOLEAN     NOT NULL DEFAULT FALSE,

    -- Audit
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ
);

CREATE INDEX contacts_club_id_idx          ON soccer_leads.contacts (club_id);
CREATE INDEX contacts_club_primary_idx     ON soccer_leads.contacts (club_id, is_primary);
CREATE INDEX contacts_active_idx           ON soccer_leads.contacts (id) WHERE deleted_at IS NULL;

CREATE TRIGGER contacts_updated_at
    BEFORE UPDATE ON soccer_leads.contacts
    FOR EACH ROW EXECUTE FUNCTION soccer_leads.set_updated_at();

-- =============================================================================
-- emails
-- =============================================================================

CREATE TABLE soccer_leads.emails (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Polymorphic owner — at least one must be set
    club_id          UUID        REFERENCES soccer_leads.clubs    (id) ON DELETE CASCADE,
    contact_id       UUID        REFERENCES soccer_leads.contacts (id) ON DELETE CASCADE,

    address          TEXT        NOT NULL,
    type             TEXT        NOT NULL DEFAULT 'general'
                                 CHECK (type IN ('primary', 'general', 'billing')),
    is_verified      BOOLEAN     NOT NULL DEFAULT FALSE,
    verified_at      TIMESTAMPTZ,
    mx_valid         BOOLEAN,

    -- Audit
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ,

    CONSTRAINT emails_owner_check CHECK (
        (club_id IS NOT NULL)::INT + (contact_id IS NOT NULL)::INT >= 1
    )
);

CREATE INDEX emails_address_idx            ON soccer_leads.emails (address);
CREATE INDEX emails_club_id_idx            ON soccer_leads.emails (club_id)     WHERE club_id    IS NOT NULL;
CREATE INDEX emails_contact_id_idx         ON soccer_leads.emails (contact_id)  WHERE contact_id IS NOT NULL;
CREATE INDEX emails_active_idx             ON soccer_leads.emails (id)          WHERE deleted_at IS NULL;
-- Prevent duplicate address per owner
CREATE UNIQUE INDEX emails_club_address_uidx
    ON soccer_leads.emails (club_id, lower(address))
    WHERE club_id IS NOT NULL AND deleted_at IS NULL;
CREATE UNIQUE INDEX emails_contact_address_uidx
    ON soccer_leads.emails (contact_id, lower(address))
    WHERE contact_id IS NOT NULL AND deleted_at IS NULL;

CREATE TRIGGER emails_updated_at
    BEFORE UPDATE ON soccer_leads.emails
    FOR EACH ROW EXECUTE FUNCTION soccer_leads.set_updated_at();

-- =============================================================================
-- phones
-- =============================================================================

CREATE TABLE soccer_leads.phones (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    club_id          UUID        REFERENCES soccer_leads.clubs    (id) ON DELETE CASCADE,
    contact_id       UUID        REFERENCES soccer_leads.contacts (id) ON DELETE CASCADE,

    number_e164      TEXT        NOT NULL
                                 CHECK (number_e164 ~ '^\+[1-9]\d{6,14}$'),
    type             TEXT        NOT NULL DEFAULT 'office'
                                 CHECK (type IN ('mobile', 'office', 'fax')),
    is_verified      BOOLEAN     NOT NULL DEFAULT FALSE,

    -- Audit
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ,

    CONSTRAINT phones_owner_check CHECK (
        (club_id IS NOT NULL)::INT + (contact_id IS NOT NULL)::INT >= 1
    )
);

CREATE INDEX phones_number_idx             ON soccer_leads.phones (number_e164);
CREATE INDEX phones_club_id_idx            ON soccer_leads.phones (club_id)    WHERE club_id    IS NOT NULL;
CREATE INDEX phones_contact_id_idx         ON soccer_leads.phones (contact_id) WHERE contact_id IS NOT NULL;
CREATE INDEX phones_active_idx             ON soccer_leads.phones (id)         WHERE deleted_at IS NULL;

CREATE TRIGGER phones_updated_at
    BEFORE UPDATE ON soccer_leads.phones
    FOR EACH ROW EXECUTE FUNCTION soccer_leads.set_updated_at();

-- =============================================================================
-- social_profiles
-- =============================================================================

CREATE TABLE soccer_leads.social_profiles (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    club_id          UUID        REFERENCES soccer_leads.clubs    (id) ON DELETE CASCADE,
    contact_id       UUID        REFERENCES soccer_leads.contacts (id) ON DELETE CASCADE,

    platform         TEXT        NOT NULL
                                 CHECK (platform IN (
                                     'twitter', 'instagram', 'facebook',
                                     'linkedin', 'youtube', 'tiktok', 'other'
                                 )),
    handle           TEXT,
    profile_url      TEXT,
    followers_count  INT         CHECK (followers_count >= 0),
    is_verified      BOOLEAN     NOT NULL DEFAULT FALSE,

    -- Audit
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ,

    CONSTRAINT social_profiles_owner_check CHECK (
        (club_id IS NOT NULL)::INT + (contact_id IS NOT NULL)::INT >= 1
    )
);

CREATE INDEX social_profiles_platform_handle_idx
    ON soccer_leads.social_profiles (platform, handle);
CREATE INDEX social_profiles_club_id_idx
    ON soccer_leads.social_profiles (club_id)    WHERE club_id    IS NOT NULL;
CREATE INDEX social_profiles_contact_id_idx
    ON soccer_leads.social_profiles (contact_id) WHERE contact_id IS NOT NULL;
CREATE UNIQUE INDEX social_profiles_club_platform_uidx
    ON soccer_leads.social_profiles (club_id, platform)
    WHERE club_id IS NOT NULL AND deleted_at IS NULL;
CREATE UNIQUE INDEX social_profiles_contact_platform_uidx
    ON soccer_leads.social_profiles (contact_id, platform)
    WHERE contact_id IS NOT NULL AND deleted_at IS NULL;

CREATE TRIGGER social_profiles_updated_at
    BEFORE UPDATE ON soccer_leads.social_profiles
    FOR EACH ROW EXECUTE FUNCTION soccer_leads.set_updated_at();

-- =============================================================================
-- crawl_jobs
-- =============================================================================

CREATE TABLE soccer_leads.crawl_jobs (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    spider_name      TEXT        NOT NULL,
    status           TEXT        NOT NULL DEFAULT 'pending'
                                 CHECK (status IN ('pending', 'running', 'done', 'failed')),
    config           JSONB       NOT NULL DEFAULT '{}',

    pages_crawled    INT         NOT NULL DEFAULT 0 CHECK (pages_crawled >= 0),
    pages_failed     INT         NOT NULL DEFAULT 0 CHECK (pages_failed  >= 0),
    error_message    TEXT,

    started_at       TIMESTAMPTZ,
    finished_at      TIMESTAMPTZ,

    -- Audit
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ
);

CREATE INDEX crawl_jobs_spider_status_idx  ON soccer_leads.crawl_jobs (spider_name, status);
CREATE INDEX crawl_jobs_status_idx         ON soccer_leads.crawl_jobs (status);
CREATE INDEX crawl_jobs_started_at_idx     ON soccer_leads.crawl_jobs (started_at DESC);

CREATE TRIGGER crawl_jobs_updated_at
    BEFORE UPDATE ON soccer_leads.crawl_jobs
    FOR EACH ROW EXECUTE FUNCTION soccer_leads.set_updated_at();

-- =============================================================================
-- crawl_results
-- =============================================================================

CREATE TABLE soccer_leads.crawl_results (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    crawl_job_id     UUID        NOT NULL REFERENCES soccer_leads.crawl_jobs (id) ON DELETE CASCADE,
    -- Populated after AI extraction links the page to a club
    club_id          UUID        REFERENCES soccer_leads.clubs (id) ON DELETE SET NULL,

    url              TEXT        NOT NULL,
    -- SHA-256 of the canonicalized URL — prevents duplicate fetches
    url_fingerprint  TEXT        NOT NULL,
    http_status      INT,
    content_type     TEXT,
    s3_key           TEXT,

    extract_status   TEXT        NOT NULL DEFAULT 'pending'
                                 CHECK (extract_status IN (
                                     'pending', 'extracted', 'failed', 'skipped'
                                 )),
    extracted_data   JSONB,

    crawled_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT crawl_results_url_fingerprint_key UNIQUE (url_fingerprint)
);

CREATE UNIQUE INDEX crawl_results_fingerprint_uidx
    ON soccer_leads.crawl_results (url_fingerprint);
CREATE INDEX crawl_results_crawl_job_idx
    ON soccer_leads.crawl_results (crawl_job_id);
CREATE INDEX crawl_results_extract_status_idx
    ON soccer_leads.crawl_results (extract_status);
CREATE INDEX crawl_results_club_id_idx
    ON soccer_leads.crawl_results (club_id) WHERE club_id IS NOT NULL;
CREATE INDEX crawl_results_crawled_at_idx
    ON soccer_leads.crawl_results (crawled_at DESC);

CREATE TRIGGER crawl_results_updated_at
    BEFORE UPDATE ON soccer_leads.crawl_results
    FOR EACH ROW EXECUTE FUNCTION soccer_leads.set_updated_at();

-- =============================================================================
-- enrichment_data
-- =============================================================================

CREATE TABLE soccer_leads.enrichment_data (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    club_id          UUID        REFERENCES soccer_leads.clubs    (id) ON DELETE CASCADE,
    contact_id       UUID        REFERENCES soccer_leads.contacts (id) ON DELETE CASCADE,

    provider         TEXT        NOT NULL
                                 CHECK (provider IN (
                                     'clearbit', 'hunter', 'fullcontact',
                                     'apollo', 'manual', 'other'
                                 )),
    payload          JSONB       NOT NULL DEFAULT '{}',
    fetched_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Audit
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT enrichment_data_owner_check CHECK (
        (club_id IS NOT NULL)::INT + (contact_id IS NOT NULL)::INT >= 1
    )
);

CREATE INDEX enrichment_club_provider_idx
    ON soccer_leads.enrichment_data (club_id, provider)    WHERE club_id    IS NOT NULL;
CREATE INDEX enrichment_contact_provider_idx
    ON soccer_leads.enrichment_data (contact_id, provider) WHERE contact_id IS NOT NULL;
CREATE INDEX enrichment_fetched_at_idx
    ON soccer_leads.enrichment_data (fetched_at DESC);

CREATE TRIGGER enrichment_data_updated_at
    BEFORE UPDATE ON soccer_leads.enrichment_data
    FOR EACH ROW EXECUTE FUNCTION soccer_leads.set_updated_at();

-- =============================================================================
-- lead_scores
-- =============================================================================

CREATE TABLE soccer_leads.lead_scores (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id             UUID        NOT NULL UNIQUE
                                    REFERENCES soccer_leads.clubs (id) ON DELETE CASCADE,

    -- Composite score
    score               FLOAT       NOT NULL CHECK (score BETWEEN 0 AND 100),
    tier                TEXT        NOT NULL CHECK (tier IN ('COLD', 'WARM', 'HOT')),

    -- Dimensional scores (each 0–100)
    completeness_score  FLOAT       CHECK (completeness_score BETWEEN 0 AND 100),
    contact_score       FLOAT       CHECK (contact_score      BETWEEN 0 AND 100),
    program_score       FLOAT       CHECK (program_score      BETWEEN 0 AND 100),
    member_score        FLOAT       CHECK (member_score       BETWEEN 0 AND 100),
    recency_score       FLOAT       CHECK (recency_score      BETWEEN 0 AND 100),

    score_breakdown     JSONB       NOT NULL DEFAULT '{}',
    model_version       TEXT,
    scored_at           TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX lead_scores_club_uidx
    ON soccer_leads.lead_scores (club_id);
CREATE INDEX lead_scores_tier_score_idx
    ON soccer_leads.lead_scores (tier, score DESC);
CREATE INDEX lead_scores_scored_at_idx
    ON soccer_leads.lead_scores (scored_at DESC);

CREATE TRIGGER lead_scores_updated_at
    BEFORE UPDATE ON soccer_leads.lead_scores
    FOR EACH ROW EXECUTE FUNCTION soccer_leads.set_updated_at();
