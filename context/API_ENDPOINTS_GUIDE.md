# Upwork Automation REST API Endpoints Guide

This document describes all REST API endpoints available in the Upwork Lead Discovery and Decision-Maker Scoring Platform. It explains what each endpoint does, its input data and parameters, and provides example request payloads, `curl` commands, and response structures.

---

## 1. Overview and Architecture

The platform processes Upwork jobs through an autonomous or human-in-the-loop pipeline:

1. **Authentication & Session Management**: Manages persistent Playwright session states (`data/sessions/session_{user}.json`) and rate limit health.
2. **Feed Scraping (Stage 1)**: Scrapes Upwork search feeds using keywords and extracts candidate job cards.
3. **Deep Scraping & Contract History Expansion (Stage 2)**: Expands up to 30+ past client contracts, isolating feedback reviews strictly before the `To freelancer:` marker.
4. **NLP Intelligence Mining (Stage 3)**: Uses spaCy NER and linguistic patterns to detect client names, company names, and agency indicators.
5. **Human-in-the-Loop Confirmation**: Allows human validation or automatic confirmation of extracted client entities.
6. **LinkedIn Decision-Maker Harvesting (Stage 4)**: Maps locations to LinkedIn GeoURNs and executes prioritized Google X-Ray searches via SerpAPI.
7. **4-Factor Scoring Engine**: Evaluates candidates across Name (40%), Location (35%), Role (15%), and Company (10%).
8. **Dual Delivery & Excel Export (Stage 5)**: Delivers both the Primary Resolved Decision-Maker (Tier A) and Potential Candidates (Tier B/C), exporting to a 46-column master Excel sheet.

- **Base URL**: `http://localhost:8000`
- **Interactive Swagger Documentation**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

---

## 2. Authentication and Session Endpoints (`/api/v1/auth`)

### 2.1 List Stored User Sessions
- **Method**: `GET`
- **Endpoint**: `/api/v1/auth/sessions`
- **Description**: Scans the `data/sessions/` directory and returns metadata (user identifier, cookie count, file name, timestamp) for all available user sessions.

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/auth/sessions" \
  -H "Accept: application/json"
```

#### Example Response
```json
[
  {
    "user_identifier": "test_user_example_com",
    "cookie_count": 84,
    "is_present": true,
    "last_modified": 1793253068.99,
    "file_name": "session_test_user_example_com.json"
  }
]
```

---

### 2.2 Get Session Status
- **Method**: `GET`
- **Endpoint**: `/api/v1/auth/status`
- **Description**: Returns local session storage state, cookie count, and rate limit health for a given user identifier without making live network requests.

#### Query Parameters
| Parameter | Type | Required | Description |
|---|---|---|---|
| `user_identifier` | string | No | Optional user identifier (e.g. `'test_user_example_com'`) |

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/auth/status?user_identifier=test_user_example_com" \
  -H "Accept: application/json"
```

#### Example Response
```json
{
  "is_authenticated": true,
  "session_file_exists": true,
  "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
  "rate_limit_health": "GREEN",
  "message": "Active session found with 18 cookies."
}
```

---

### 2.2 Verify Session Liveness
- **Method**: `POST`
- **Endpoint**: `/api/v1/auth/verify`
- **Description**: Launches a headless Playwright instance to verify that stored cookies pass Upwork anti-bot and Cloudflare checks.

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/auth/verify" \
  -H "Accept: application/json"
```

#### Example Response
```json
{
  "is_authenticated": true,
  "session_file_exists": true,
  "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
  "rate_limit_health": "GREEN",
  "message": "Session active and validated against Upwork live search."
}
```

---

### 2.3 Direct Session / Cookie Import
- **Method**: `POST`
- **Endpoint**: `/api/v1/auth/session/import`
- **Description**: Directly imports Upwork session cookies or a Playwright storage state JSON, persisting them to `data/sessions/session_{username}.json` for immediate use.

#### Request Body Schema
| Field | Type | Required | Description |
|---|---|---|---|
| `user_identifier` | string | Yes | Username or email to identify the session |
| `session_data` | object/list | Yes | JSON containing cookies list or Playwright storage state |

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/auth/session/import" \
  -H "Content-Type: application/json" \
  -d '{
    "user_identifier": "user@example.com",
    "session_data": {
      "cookies": [
        {"name": "oauth2_global_js_token", "value": "token...", "domain": ".upwork.com", "path": "/"}
      ]
    }
  }'
```

---

### 2.4 Automated Login
- **Method**: `POST`
- **Endpoint**: `/api/v1/auth/login`
- **Description**: Automates login via Playwright, solves authentication challenges, and saves authenticated session cookies to `data/sessions/session_{username}.json`.

#### Request Body Schema
| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | Yes | Upwork account username or email |
| `password` | string | Yes | Upwork password (minimum 6 characters) |
| `security_answer` | string | No | Security question answer or 2FA PIN |
| `remember_session` | boolean | No | Persist cookies to local storage (default: `true`) |

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_email@domain.com",
    "password": "your_password",
    "security_answer": "your_answer",
    "remember_session": true
  }'
```

#### Example Response
```json
{
  "is_authenticated": true,
  "session_file_exists": true,
  "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
  "rate_limit_health": "GREEN",
  "message": "Login successful for user your_email@domain.com"
}
```

---

## 3. Job Feed Scraping Endpoints (`/api/v1/jobs`)

### 3.1 Search Job Feed
- **Method**: `POST`
- **Endpoint**: `/api/v1/jobs/search`
- **Description**: Scrapes Upwork search results for given keywords, writes Stage 1 snapshot JSON to `data/snapshots/stage1_search/`, and registers the search run in PostgreSQL.

#### Request Body Schema
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | Yes | `"automation"` | Search keyword query |
| `limit` | integer | No | `15` | Maximum job cards to harvest (1 - 50) |
| `expand_history` | boolean | No | `true` | Whether to flag jobs for history expansion |
| `force_live` | boolean | No | `false` | Bypass local snapshot cache and fetch live |
| `user_identifier` | string | No | `null` | Optional identifier for multi-tenant sessions |

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/jobs/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Senior Backend Engineer",
    "limit": 5,
    "force_live": false
  }'
```

#### Example Response
```json
{
  "query": "Senior Backend Engineer",
  "scraped_count": 5,
  "jobs": [
    {
      "job_uid": "2115080556493477594",
      "job_url": "https://www.upwork.com/jobs/~022115080556493477594",
      "title": "Senior Backend Application Engineer",
      "client": {
        "city": "Budapest",
        "country": "Hungary",
        "total_spent_usd": "157000.00"
      }
    }
  ]
}
```

---

### 3.2 Deep Expand Job Details and History
- **Method**: `POST`
- **Endpoint**: `/api/v1/jobs/{job_uid}/expand`
- **Description**: Performs deep scraping of a single job. Navigates via Playwright, clicks pagination to expand up to 30+ past client contracts, cleans client feedback, saves Stage 2 JSON snapshot, and syncs into PostgreSQL.

#### Parameters
| Parameter | Location | Type | Required | Default | Description |
|---|---|---|---|---|---|
| `job_uid` | Path | string | Yes | - | Upwork job identifier (e.g. `2115080556493477594`) |
| `job_url` | Query | string | Yes | - | Canonical Upwork job URL |
| `force_live` | Query | boolean | No | `false` | Bypass cached snapshot |
| `user_identifier` | Query | string | No | `null` | Multi-tenant session identifier |

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/jobs/2115080556493477594/expand?job_url=https%3A%2F%2Fwww.upwork.com%2Fjobs%2F~022115080556493477594&force_live=false" \
  -H "Accept: application/json"
```

#### Example Response
```json
{
  "status": "EXPANDED_SUCCESSFULLY",
  "job_uid": "2115080556493477594",
  "title": "Senior Backend Application Engineer",
  "client_city": "Budapest",
  "client_country": "Hungary",
  "client_total_spent": "157000.00",
  "total_contracts_extracted": 35,
  "in_progress_count": 3,
  "completed_count": 32,
  "snapshot_path": "data/snapshots/stage2_jobs/2115080556493477594_detailed.json"
}
```

---

### 3.3 Get Job by UID
- **Method**: `GET`
- **Endpoint**: `/api/v1/jobs/{job_uid}`
- **Description**: Retrieves full job details, client profile, intelligence, and candidates from PostgreSQL.

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/2115080556493477594" \
  -H "Accept: application/json"
```

---

## 4. Intelligence and Human-in-the-Loop Endpoints (`/api/v1/intelligence`)

### 4.1 Extract Job Intelligence
- **Method**: `GET`
- **Endpoint**: `/api/v1/intelligence/{job_uid}`
- **Description**: Runs spaCy NLP and linguistic regex mining over the job description and partitioned client feedback history. Returns suggested client name, suggested company name, confidence score, and candidate lists.

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/intelligence/2115080556493477594" \
  -H "Accept: application/json"
```

#### Example Response
```json
{
  "job_id": "4b63ff5a-93be-4395-88bf-98f98a2eef6b",
  "job_uid": "2115080556493477594",
  "suggested_client_name": "Zoltan",
  "suggested_company_name": "Skybound Tech",
  "suggested_role": "CTO",
  "client_name_candidates": [
    {
      "name": "Zoltan",
      "confidence": "0.95",
      "source": "Linguistic Regex Patterns",
      "mention_count": 6,
      "supporting_context": "Zoltan is a great client to work with, clear requirements..."
    }
  ],
  "company_candidates": [
    {
      "name": "Skybound Tech",
      "confidence": "0.85",
      "source": "spaCy NER + Clean Title",
      "mention_count": 1,
      "supporting_context": "At Skybound Tech we build scalable backend microservices..."
    }
  ],
  "is_agency": false,
  "agency_detection_reason": null,
  "approval_status": "PENDING"
}
```

---

### 4.2 Human Confirmation / Override
- **Method**: `POST`
- **Endpoint**: `/api/v1/intelligence/confirm`
- **Description**: Human-in-the-loop checkpoint. Confirms or overrides the suggested person name and organization name before running LinkedIn discovery.

#### Request Body Schema
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `job_id` | UUID | Yes | - | Internal UUID of the job |
| `confirmed_client_name` | string | Yes | - | Verified client person name (minimum 2 characters) |
| `confirmed_company_name` | string | No | `null` | Verified client company name |
| `target_role` | string | No | `"CTO"` | Target decision-maker role |

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/intelligence/confirm" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "4b63ff5a-93be-4395-88bf-98f98a2eef6b",
    "confirmed_client_name": "Zoltan",
    "confirmed_company_name": "Skybound Tech",
    "target_role": "CTO"
  }'
```

#### Example Response
```json
{
  "id": "c1a93e3d-7411-469a-9e79-c793ffcefa12",
  "job_id": "4b63ff5a-93be-4395-88bf-98f98a2eef6b",
  "confirmed_client_name": "Zoltan",
  "confirmed_company_name": "Skybound Tech",
  "target_role": "CTO",
  "name_confidence": "0.95",
  "name_mentions_count": 6,
  "approval_status": "APPROVED",
  "confirmed_at": "2026-10-29T12:00:00Z"
}
```

---

## 5. Decision-Maker Discovery Endpoints (`/api/v1/leads`)

### 5.1 Discover Decision-Makers
- **Method**: `POST`
- **Endpoint**: `/api/v1/leads/{job_uid}/discover`
- **Description**: Executes the decision-maker discovery process:
  1. Resolves location to LinkedIn GeoURN and generates direct search URLs.
  2. Runs SerpAPI Google X-Ray queries.
  3. Evaluates candidates using the 4-factor scoring model.
  4. Commits candidates to PostgreSQL and writes Stage 4 snapshot JSON.
  5. Returns Dual Delivery: Primary Resolved Candidate (Tier A) + Potential Candidates (Tier B/C).

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/leads/2115080556493477594/discover" \
  -H "Accept: application/json"
```

#### Example Response
```json
{
  "job_id": "4b63ff5a-93be-4395-88bf-98f98a2eef6b",
  "job_uid": "2115080556493477594",
  "client_name": "Zoltan",
  "location": "Budapest, Hungary",
  "resolved_candidate": {
    "rank_order": 1,
    "full_name": "Zoltan B.",
    "headline": "CTO & Co-Founder at Skybound Tech",
    "profile_location": "Budapest, Hungary",
    "linkedin_url": "https://www.linkedin.com/in/zoltan-b",
    "match_score": "80.5",
    "confidence": "0.81",
    "tier": "Tier A",
    "is_primary_resolved": true,
    "scoring_reasons": [
      "Exact First Name match (90%): 'Zoltan' vs 'Zoltan B.'",
      "Direct city match: 'Budapest' in profile location",
      "Top-tier decision-maker title: 'CTO'"
    ]
  },
  "potential_candidates": [
    {
      "rank_order": 2,
      "full_name": "Zoltan Nagy",
      "headline": "Senior Software Architect",
      "profile_location": "Budapest, Hungary",
      "linkedin_url": "https://www.linkedin.com/in/zoltan-nagy",
      "match_score": "65.0",
      "confidence": "0.65",
      "tier": "Tier B",
      "is_primary_resolved": false
    }
  ],
  "direct_linkedin_search_urls": [
    "https://www.linkedin.com/search/results/people/?keywords=Zoltan&geoUrn=%5B%22100288700%22%5D&origin=FACETED_SEARCH"
  ],
  "excel_download_url": "/api/v1/leads/2115080556493477594/export"
}
```

---

### 5.2 Export Leads to Master Excel
- **Method**: `GET`
- **Endpoint**: `/api/v1/leads/export`
- **Description**: Downloads the sales-ready 46-column Master Excel Workbook (`.xlsx`) containing all analyzed leads with optional filters.

#### Query Parameters
| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `min_spend` | decimal | No | `null` | Filter clients by minimum spend in USD |
| `tier` | string | No | `null` | Filter by match tier (e.g. `'Tier A'`) |
| `country` | string | No | `null` | Filter by client country (e.g. `'United States'`) |
| `only_primary` | boolean | No | `false` | Export only the primary resolved candidate per job |

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/leads/export?min_spend=10000&tier=Tier%20A&only_primary=true" \
  -o "master_leads.xlsx"
```

---

### 5.3 Export Single Job Lead to Excel
- **Method**: `GET`
- **Endpoint**: `/api/v1/leads/{job_uid}/export`
- **Description**: Downloads the 46-column Excel workbook for a single job lead.

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/leads/2115080556493477594/export?only_primary=false" \
  -o "job_leads.xlsx"
```

---

## 6. End-to-End Pipeline Endpoints (`/api/v1/pipelines`)

### 6.1 Single Job Pipeline (`/job-run`)
- **Method**: `POST`
- **Endpoint**: `/api/v1/pipelines/job-run`
- **Description**: Runs the full end-to-end pipeline on a single Upwork job URL in one step:
  - Scrapes job & client details.
  - Expands client contract history.
  - Extracts and auto-confirms client and company entities.
  - Searches LinkedIn candidates via SerpAPI.
  - Scores candidates and persists Tier A / Potential candidates.
  - Generates the Master Excel file.

#### Request Body Schema
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `job_url` | string | Yes | - | Canonical Upwork job URL |
| `auto_confirm` | boolean | No | `true` | Automatically confirm highest-confidence client name |
| `apply_delay` | boolean | No | `false` | Apply anti-blocking jitter delay |
| `user_identifier` | string | No | `null` | Multi-tenant session identifier |

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/pipelines/job-run" \
  -H "Content-Type: application/json" \
  -d '{
    "job_url": "https://www.upwork.com/jobs/~022115080556493477594",
    "auto_confirm": true,
    "apply_delay": false
  }'
```

#### Example Response
```json
{
  "job_uid": "2115080556493477594",
  "job_title": "Senior Backend Application Engineer",
  "job_url": "https://www.upwork.com/jobs/~022115080556493477594",
  "client_name": "Zoltan",
  "company_name": "Skybound Tech",
  "total_contracts": 35,
  "total_candidates": 3,
  "primary_resolved_name": "Zoltan B.",
  "primary_resolved_score": 80.5,
  "jitter_slept_seconds": 0,
  "status": "COMPLETED",
  "excel_export_path": "data/exports/master_leads_20261029_120000.xlsx"
}
```

---

### 6.2 Autonomous Batch Pipeline (`/batch-run`)
- **Method**: `POST`
- **Endpoint**: `/api/v1/pipelines/batch-run`
- **Description**: Automates end-to-end discovery across multiple jobs from an Upwork search feed with anti-blocking delays.

#### Request Body Schema
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `search_query` | string | Yes | - | Upwork search query (e.g. `'fastapi'`, `'python'`) |
| `max_jobs` | integer | No | `5` | Maximum number of jobs to process (1 - 30) |
| `min_spend` | decimal | No | `null` | Filter out clients spending less than this amount |
| `auto_confirm` | boolean | No | `true` | Auto-confirm extracted entities |
| `apply_delay` | boolean | No | `true` | Apply anti-blocking delay (8 - 15 seconds) |
| `user_identifier` | string | No | `null` | Multi-tenant session identifier |

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/pipelines/batch-run" \
  -H "Content-Type: application/json" \
  -d '{
    "search_query": "Python FastAPI",
    "max_jobs": 5,
    "min_spend": 5000.0,
    "auto_confirm": true,
    "apply_delay": true
  }'
```

#### Example Response
```json
{
  "run_id": "7fa9c12b-3e54-4f01-9bc8-81203405c110",
  "search_query": "Python FastAPI",
  "status": "COMPLETED",
  "total_jobs_scraped": 5,
  "successful_jobs": 5,
  "failed_jobs": 0,
  "jobs_processed": [
    {
      "job_uid": "2115080556493477594",
      "status": "SUCCESS",
      "primary_candidate": "Zoltan B.",
      "score": 80.5
    }
  ],
  "excel_export_path": "data/exports/batch_7fa9c12b-3e54-4f01-9bc8-81203405c110.xlsx"
}
```

---

### 6.3 Pipeline Run Status (`/status/{run_id}`)
- **Method**: `GET`
- **Endpoint**: `/api/v1/pipelines/status/{run_id}`
- **Description**: Polls the real-time execution status and progress of an active or completed batch run.

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/pipelines/status/7fa9c12b-3e54-4f01-9bc8-81203405c110" \
  -H "Accept: application/json"
```

---

## 7. Health Check (`/health`)

### Root Liveness Check
- **Method**: `GET`
- **Endpoint**: `/health`
- **Description**: Verifies that the API service is online and database connections are operational.

#### Example Request
```bash
curl -X GET "http://localhost:8000/health"
```

#### Example Response
```json
{
  "status": "ONLINE",
  "project": "Upwork Lead Intelligence Platform",
  "version": "1.0.0"
}
```

---

## 8. Summary of Workflow Scenarios

### Scenario A: Fully Autonomous Single Job Run
Execute everything from URL to Excel with one API call:
```bash
curl -X POST "http://localhost:8000/api/v1/pipelines/job-run" \
  -H "Content-Type: application/json" \
  -d '{"job_url": "https://www.upwork.com/jobs/~022115080556493477594"}'
```

### Scenario B: Interactive Human-in-the-Loop Pipeline
For high-value enterprise leads requiring manual review before LinkedIn enrichment:
1. **Scrape & Expand**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/jobs/2115080556493477594/expand?job_url=https%3A%2F%2Fwww.upwork.com%2Fjobs%2F~022115080556493477594"
   ```
2. **Review Extracted Intelligence**:
   ```bash
   curl -X GET "http://localhost:8000/api/v1/intelligence/2115080556493477594"
   ```
3. **Confirm or Override Entity Names**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/intelligence/confirm" \
     -H "Content-Type: application/json" \
     -d '{"job_id": "<JOB_UUID>", "confirmed_client_name": "Zoltan", "confirmed_company_name": "Skybound Tech"}'
   ```
4. **Discover Decision-Makers**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/leads/2115080556493477594/discover"
   ```
5. **Download Excel Report**:
   ```bash
   curl -X GET "http://localhost:8000/api/v1/leads/2115080556493477594/export" -o "lead.xlsx"
   ```

