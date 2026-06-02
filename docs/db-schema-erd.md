# Soccer Club Lead Gen — Database ERD

All tables live in the `soccer_leads` schema on PostgreSQL 16+.
Extensions required: `pgcrypto`, `pg_trgm`.

```mermaid
erDiagram
    clubs {
        uuid        id              PK
        text        name            "NOT NULL"
        text        slug            "UNIQUE NOT NULL"
        text        website_url
        text        description
        text        division
        text        league_affiliation
        int         founded_year
        int         member_count_est
        int         team_count_est
        text[]      age_groups
        text[]      program_types
        text        street_address
        text        city
        char2       state_code
        text        zip_code
        char2       country_code    "default US"
        float       latitude
        float       longitude
        text        data_source
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at      "soft delete"
    }

    contacts {
        uuid        id              PK
        uuid        club_id         FK
        text        first_name
        text        last_name
        text        role
        bool        is_primary      "default false"
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    emails {
        uuid        id              PK
        uuid        club_id         FK "nullable"
        uuid        contact_id      FK "nullable"
        text        address         "NOT NULL"
        text        type            "primary|general|billing"
        bool        is_verified
        timestamptz verified_at
        bool        mx_valid
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    phones {
        uuid        id              PK
        uuid        club_id         FK "nullable"
        uuid        contact_id      FK "nullable"
        text        number_e164     "NOT NULL"
        text        type            "mobile|office|fax"
        bool        is_verified
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    social_profiles {
        uuid        id              PK
        uuid        club_id         FK "nullable"
        uuid        contact_id      FK "nullable"
        text        platform        "NOT NULL"
        text        handle
        text        profile_url
        int         followers_count
        bool        is_verified
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    crawl_jobs {
        uuid        id              PK
        text        spider_name     "NOT NULL"
        text        status          "pending|running|done|failed"
        jsonb       config
        int         pages_crawled
        int         pages_failed
        text        error_message
        timestamptz started_at
        timestamptz finished_at
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    crawl_results {
        uuid        id              PK
        uuid        crawl_job_id    FK
        uuid        club_id         FK "nullable — set post-extraction"
        text        url             "NOT NULL"
        text        url_fingerprint "UNIQUE NOT NULL"
        int         http_status
        text        content_type
        text        s3_key
        text        extract_status  "pending|extracted|failed|skipped"
        jsonb       extracted_data
        timestamptz crawled_at
        timestamptz created_at
        timestamptz updated_at
    }

    enrichment_data {
        uuid        id              PK
        uuid        club_id         FK "nullable"
        uuid        contact_id      FK "nullable"
        text        provider        "NOT NULL"
        jsonb       payload
        timestamptz fetched_at
        timestamptz created_at
        timestamptz updated_at
    }

    lead_scores {
        uuid        id                  PK
        uuid        club_id             FK "UNIQUE"
        float       score               "0–100"
        text        tier                "COLD|WARM|HOT"
        float       completeness_score
        float       contact_score
        float       program_score
        float       member_score
        float       recency_score
        jsonb       score_breakdown
        text        model_version
        timestamptz scored_at
        timestamptz created_at
        timestamptz updated_at
    }

    clubs       ||--o{ contacts         : "has"
    clubs       ||--o{ emails           : "has"
    clubs       ||--o{ phones           : "has"
    clubs       ||--o{ social_profiles  : "has"
    clubs       ||--o{ crawl_results    : "extracted into"
    clubs       ||--o{ enrichment_data  : "enriched by"
    clubs       ||--o|  lead_scores     : "scored as"
    contacts    ||--o{ emails           : "has"
    contacts    ||--o{ phones           : "has"
    contacts    ||--o{ social_profiles  : "has"
    contacts    ||--o{ enrichment_data  : "enriched by"
    crawl_jobs  ||--o{ crawl_results    : "produces"
```

## Index Summary

| Table | Index | Type | Notes |
|---|---|---|---|
| clubs | `slug` | UNIQUE BTREE | |
| clubs | `state_code, division` | BTREE | Filter queries |
| clubs | `deleted_at` WHERE NULL | PARTIAL BTREE | Active-row queries |
| clubs | `name` gin_trgm_ops | GIN | Fuzzy name search |
| contacts | `club_id` | BTREE | |
| contacts | `club_id, is_primary` | BTREE | Primary contact lookup |
| contacts | `deleted_at` WHERE NULL | PARTIAL BTREE | |
| emails | `address` | BTREE | Dedup |
| emails | `club_id` WHERE NOT NULL | PARTIAL BTREE | |
| emails | `contact_id` WHERE NOT NULL | PARTIAL BTREE | |
| phones | `number_e164` | BTREE | Dedup |
| phones | `club_id` WHERE NOT NULL | PARTIAL BTREE | |
| social_profiles | `platform, handle` | BTREE | Dedup |
| social_profiles | `club_id` WHERE NOT NULL | PARTIAL BTREE | |
| crawl_jobs | `spider_name, status` | BTREE | |
| crawl_jobs | `started_at DESC` | BTREE | |
| crawl_results | `url_fingerprint` | UNIQUE BTREE | |
| crawl_results | `crawl_job_id` | BTREE | |
| crawl_results | `extract_status` | BTREE | |
| crawl_results | `club_id` WHERE NOT NULL | PARTIAL BTREE | |
| enrichment_data | `club_id, provider` | BTREE | |
| enrichment_data | `contact_id, provider` | BTREE | |
| lead_scores | `club_id` | UNIQUE BTREE | One score per club |
| lead_scores | `tier, score DESC` | BTREE | Ranked list queries |
