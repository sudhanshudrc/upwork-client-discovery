# Frontend Developer Query: API Endpoints Execution and Response Log

**Date & Time**: 2026-10-29 13:10:00 UTC+5:30  
**Target Query**: `Frontend Developer`  
**Test Scope**: End-to-end execution across all platform REST API endpoints.

---

## 1. Execution Overview and Test Matrix

The following endpoints were exercised with the `Frontend Developer` query and associated harvested job postings:

| Step | Method | Endpoint | Tested Job UID | Result Status |
|---|---|---|---|---|
| 1 | `POST` | `/api/v1/jobs/search` | - | `200 OK` (3 jobs extracted) |
| 2 | `POST` | `/api/v1/jobs/{job_uid}/expand` | `2115360423948389981` | `200 OK` (5 contracts expanded) |
| 3 | `GET` | `/api/v1/jobs/{job_uid}` | `2115360423948389981` | `200 OK` (Full relational record) |
| 4 | `GET` | `/api/v1/intelligence/{job_uid}` | `2115360423948389981` | `200 OK` (Extracted client "Martin") |
| 5 | `POST` | `/api/v1/intelligence/confirm` | `2115302368812535389` | `200 OK` (Target confirmed in PostgreSQL) |
| 6 | `POST` | `/api/v1/leads/{job_uid}/discover` | `2115360423948389981` | `200 OK` (Scored 3 LinkedIn candidates) |
| 7 | `GET` | `/api/v1/leads/{job_uid}/export` | `2115360423948389981` | `200 OK` (Downloaded 10.2 KB Excel file) |
| 8 | `POST` | `/api/v1/pipelines/job-run` | `2115360423948389981` | `200 OK` (End-to-end pipeline completed) |
| 9 | `POST` | `/api/v1/pipelines/job-run` | `2115295826369384029` | `200 OK` (Cloudflare blocked fixture encountered) |

---

## 2. Endpoint Responses Log

### 2.1 Job Feed Search (`POST /api/v1/jobs/search`)
- **Payload**:
```json
{
  "query": "Frontend Developer",
  "limit": 3,
  "force_live": false
}
```
- **Response**:
```json
{
  "run_id": "run_20261029_073744",
  "db_run_id": "41370098-8f79-4e68-912a-0df09ba60090",
  "query": "Frontend Developer",
  "total_extracted": 3,
  "snapshot_path": "/app/data/snapshots/stage1_feeds/run_20261029_073744_feed.json",
  "jobs": [
    {
      "uid": "2115302368812535389",
      "title": "CRM & Sales Funnel Manager (Full-Time)",
      "url": "https://www.upwork.com/jobs/~022115302368812535389",
      "budget": "Fixed price",
      "experience_level": "Expert",
      "client_spent": null,
      "snippet": "We are looking for a full-time CRM & Sales Funnel Manager to oversee and optimize the entire customer journey, from lead acquisition to final conversi..."
    },
    {
      "uid": "2115295826369384029",
      "title": "GoHighLevel Expert – Landing Pages, Funnels & Email Automation (Ongoing)",
      "url": "https://www.upwork.com/jobs/~022115295826369384029",
      "budget": "Hourly: $15.00 - $38.00",
      "experience_level": "Intermediate",
      "client_spent": null,
      "snippet": "About Us We are an Australian business group operating across retail and digital marketing. We are looking for an experienced, self-managed GoHighLeve..."
    },
    {
      "uid": "2115295609736866961",
      "title": "API Integration Specialist - Zapier / Webhooks (Sprout Studio to Helcim Payment Link Automation)",
      "url": "https://www.upwork.com/jobs/~022115295609736866961",
      "budget": "Fixed price",
      "experience_level": "Intermediate",
      "client_spent": null,
      "snippet": "I am looking for an automation developer to bridge a workflow gap between Sprout Studio and my payment gateway, Helcim, using Zapier or Make.com. Spro..."
    }
  ]
}
```

---

### 2.2 Deep Job Expansion (`POST /api/v1/jobs/{job_uid}/expand`)
- **Target**: `2115360423948389981` ("Frontend Developer")
- **URL**: `https://www.upwork.com/jobs/~022115360423948389981`
- **Response**:
```json
{
  "status": "EXPANDED_SUCCESSFULLY",
  "job_uid": "2115360423948389981",
  "title": "Frontend Developer",
  "client_city": "Dubai",
  "client_country": "United Arab Emirates",
  "client_total_spent": "106000.00",
  "total_contracts_extracted": 5,
  "in_progress_count": 0,
  "completed_count": 5,
  "snapshot_path": "data/snapshots/stage2_jobs/2115360423948389981_detailed.json"
}
```

---

### 2.3 Job Retrieval from Database (`GET /api/v1/jobs/{job_uid}`)
- **Target**: `2115360423948389981`
- **Response**:
```json
{
  "job_uid": "2115360423948389981",
  "job_url": "https://www.upwork.com/jobs/~022115360423948389981",
  "title": "Frontend Developer",
  "pay_type": "Fixed-price",
  "budget_min_usd": null,
  "budget_max_usd": null,
  "experience_level": "Expert",
  "project_duration": null,
  "hours_per_week": null,
  "proposals_tier": "Less than 5",
  "interviewing_count": 0,
  "invites_sent_count": 0,
  "unanswered_invites": 0,
  "skills_tags": "",
  "description": "Summary We’re looking for a mid-level or senior Front-End Developer to join our growing tech team. You’ll be joining us early in our mission to reinvent SME finance, building a product that’s simple, reliable, and impactful. What You’ll Do • Collaborate with product designers and backend engineers to design and deliver new features. • Take part in the full user-experience process from wireframes and prototypes to release. • Help define and maintain visual guidelines to ensure consistency across the app. • Rapidly prototype user interactions and iterate based on feedback. • Participate in code reviews and contribute to improving team practices. Essential skills: • 3+ years of experience building front-end applications with React.js and JavaScript. • Strong understanding of HTML5, CSS3, and SASS. • Experience with Webpack, Babel, and modern build tools. • Comfortable consuming RESTful APIs with solid error handling. • Strong debugging, testing, and performance-optimization skills. • Experience integrating design and backend components. • Familiar with Git workflows and collaborative development. • Able to work in a fast-paced, agile environment. • Hands-on mindset — capable of building new features or services from scratch. Nice to have: • Experience in banking, fintech, or finance. • Knowledge of React Native / Expo for mobile development. • Familiarity with Azure DevOps, CI/CD pipelines, or cloud deployments. • Experience with Redux, Zustand, or other state-management tools. • Testing knowledge using Jest or React Testing Library.",
  "posted_at": null,
  "id": "ba9e37f8-1514-4ada-9014-b43a024c7827",
  "client_id": "8ba40ab3-293d-4b19-8420-0254afab9c5e",
  "created_at": "2026-10-29T07:40:05.593791Z",
  "client": {
    "city": "Dubai",
    "state": null,
    "country": "United Arab Emirates",
    "local_time": "1:29 PM",
    "total_spent_usd": "106000.00",
    "avg_hourly_rate_usd": "16.85",
    "hire_rate_pct": null,
    "total_hires": 45,
    "active_hires": 11,
    "client_rating": null,
    "total_reviews": 5,
    "payment_verified": true,
    "company_size": "Mid-sized company (10-99 people)",
    "industry": "Finance & Accounting",
    "member_since": "Member since May 19, 2019",
    "id": "8ba40ab3-293d-4b19-8420-0254afab9c5e",
    "client_uid": null,
    "created_at": "2026-10-29T07:40:05.593791Z",
    "updated_at": "2026-10-29T07:40:05.593791Z"
  },
  "contracts": [],
  "intelligence": {
    "id": "9d0e945e-a6ae-4231-b7d4-3bb4dd196988",
    "job_id": "ba9e37f8-1514-4ada-9014-b43a024c7827",
    "confirmed_client_name": "Martin",
    "confirmed_company_name": "SME",
    "target_role": "CTO",
    "name_confidence": "70.00",
    "name_mentions_count": 1,
    "name_evidence_snippet": "I appreciated the opportunity to work with Martin and his team. Project expectations and requirements were clearly defined upfront, communic...",
    "company_evidence_snippet": "You’ll be joining us early in our mission to reinvent SME finance, building a product that’s simple, reliable, and impactful.",
    "is_agency": false,
    "approval_status": "APPROVED",
    "confirmed_at": "2026-10-29T07:40:05.609557Z"
  },
  "candidates": [
    {
      "rank_order": 1,
      "full_name": "Martin Rochester",
      "headline": "Consultant at WB",
      "profile_location": "United Arab Emirates",
      "linkedin_url": "https://ae.linkedin.com/in/martin-rochester-99505917b",
      "match_score": "45.50",
      "confidence": "45.00",
      "tier": "Tier C (Low Match / Irrelevant)",
      "is_primary_resolved": false,
      "scoring_reasons": [
        "Name Match (90%): 'Martin' vs 'Martin Rochester'",
        "Location mismatch: Profile does not match Dubai",
        "Professional: 'Consultant'",
        "Company 'SME' not explicitly found in snippet"
      ]
    }
  ]
}
```

---

### 2.4 Intelligence Entity Mining (`GET /api/v1/intelligence/{job_uid}`)
- **Target**: `2115360423948389981`
- **Response**:
```json
{
  "job_id": "ba9e37f8-1514-4ada-9014-b43a024c7827",
  "job_uid": "2115360423948389981",
  "suggested_client_name": "Martin",
  "suggested_company_name": "SME",
  "suggested_role": "CTO",
  "client_name_candidates": [
    {
      "name": "Martin",
      "confidence": "80.00",
      "source": "linguistic_review_regex",
      "mention_count": 2,
      "supporting_context": "I appreciated the opportunity to work with Martin and his team. Project expectations and requirements were clearly defined upfront, communic..."
    }
  ],
  "company_candidates": [
    {
      "name": "SME",
      "confidence": "85.00",
      "source": "job_description_spacy_org",
      "mention_count": 1,
      "supporting_context": "You’ll be joining us early in our mission to reinvent SME finance, building a product that’s simple, reliable, and impactful."
    },
    {
      "name": "Webpack, Babel",
      "confidence": "85.00",
      "source": "job_description_spacy_org",
      "mention_count": 1,
      "supporting_context": "• Experience with Webpack, Babel, and modern build tools."
    }
  ],
  "is_agency": false,
  "agency_detection_reason": "Direct client posting (No agency broker language detected)",
  "approval_status": "PENDING"
}
```

---

### 2.5 Decision-Maker Discovery (`POST /api/v1/leads/{job_uid}/discover`)
- **Target**: `2115360423948389981`
- **Client Name**: `Martin`
- **Location**: `Dubai, United Arab Emirates`
- **Response**:
```json
{
  "job_id": "ba9e37f8-1514-4ada-9014-b43a024c7827",
  "job_uid": "2115360423948389981",
  "client_name": "Martin",
  "location": "Dubai, United Arab Emirates",
  "resolved_candidate": null,
  "potential_candidates": [
    {
      "rank_order": 1,
      "full_name": "Martin Rochester",
      "headline": "Consultant at WB",
      "profile_location": "United Arab Emirates",
      "linkedin_url": "https://ae.linkedin.com/in/martin-rochester-99505917b",
      "match_score": "45.50",
      "confidence": "45.00",
      "tier": "Tier C (Low Match / Irrelevant)",
      "is_primary_resolved": false,
      "scoring_reasons": [
        "Name Match (90%): 'Martin' vs 'Martin Rochester'",
        "Location mismatch: Profile does not match Dubai",
        "Professional: 'Consultant'",
        "Company 'SME' not explicitly found in snippet"
      ],
      "id": "6113e766-571c-45bc-8e61-2d607c593f98",
      "job_id": "ba9e37f8-1514-4ada-9014-b43a024c7827",
      "created_at": "2026-10-29T07:40:52.247550Z"
    },
    {
      "rank_order": 2,
      "full_name": "Shakir Mohamed",
      "headline": "AI Research and Engineering",
      "profile_location": "Research Director - AI, Science and Society",
      "linkedin_url": "https://uk.linkedin.com/in/shakirm",
      "match_score": "21.50",
      "confidence": "15.00",
      "tier": "Tier C (Low Match / Irrelevant)",
      "is_primary_resolved": false,
      "scoring_reasons": [
        "Name Match (30%): 'Martin' vs 'Shakir Mohamed'",
        "Location mismatch: Profile does not match Dubai",
        "Professional: 'Engineer'",
        "Company 'SME' not explicitly found in snippet"
      ],
      "id": "011f6dae-59b6-4816-bd08-3e09b4de1efc",
      "job_id": "ba9e37f8-1514-4ada-9014-b43a024c7827",
      "created_at": "2026-10-29T07:40:52.247550Z"
    },
    {
      "rank_order": 3,
      "full_name": "Robin Wauters",
      "headline": "Startups for Europe",
      "profile_location": "Brussels",
      "linkedin_url": "https://be.linkedin.com/in/robinwauters",
      "match_score": "19.13",
      "confidence": "15.79",
      "tier": "Tier C (Low Match / Irrelevant)",
      "is_primary_resolved": false,
      "scoring_reasons": [
        "Name Match (31%): 'Martin' vs 'Robin Wauters'",
        "Location mismatch: Profile does not match Dubai",
        "General professional profile",
        "Company 'SME' not explicitly found in snippet"
      ],
      "id": "66f4f19a-b5a9-4d41-8990-7e56a6871d36",
      "job_id": "ba9e37f8-1514-4ada-9014-b43a024c7827",
      "created_at": "2026-10-29T07:40:52.247550Z"
    }
  ],
  "direct_linkedin_search_urls": [
    "https://www.linkedin.com/search/results/people/?keywords=Martin&geoUrn=%5B%22104305776%22%5D&origin=FACETED_SEARCH",
    "https://www.linkedin.com/search/results/people/?keywords=Martin&origin=FACETED_SEARCH"
  ],
  "excel_download_url": "/api/v1/leads/2115360423948389981/export"
}
```

---

### 2.6 Excel Download (`GET /api/v1/leads/{job_uid}/export`)
- **Status**: `200 OK`
- **Content-Type**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Content-Disposition**: `attachment; filename="2115360423948389981_leads.xlsx"`
- **File Size**: `10,222 bytes` (verified on disk)

---

### 2.7 End-to-End Single Job Autonomous Run (`POST /api/v1/pipelines/job-run`)
- **Payload**:
```json
{
  "job_url": "https://www.upwork.com/jobs/~022115360423948389981",
  "auto_confirm": true,
  "apply_delay": false
}
```
- **Response**:
```json
{
  "job_uid": "2115360423948389981",
  "job_title": "Frontend Developer",
  "job_url": "https://www.upwork.com/jobs/~022115360423948389981",
  "client_name": "Martin",
  "company_name": "SME",
  "total_contracts": 5,
  "total_candidates": 3,
  "primary_resolved_name": null,
  "primary_resolved_score": null,
  "jitter_slept_seconds": 0.0,
  "status": "COMPLETED"
}
```

---

## 3. Discovered Errors & Anomalies (Saved for Discussion)

The test revealed two key anomalies that should be discussed and remediated:

### Anomaly 1: Cloudflare Challenge Fixture Parsed as Valid Job
- **Encountered on**: `POST /api/v1/pipelines/job-run` for `https://www.upwork.com/jobs/~022115295826369384029`
- **Output**:
  - `job_title`: `"Sorry, you have been blocked"`
  - `total_contracts`: `0`
  - `status`: `"COMPLETED"`
- **Root Cause**:
  In `playground/fixtures/jobs/2115295826369384029.html` (and several other 4,820-byte files), an automated request previously saved Upwork's Cloudflare challenge page (`<title>Attention Required! | Cloudflare</title>`).
  Because `force_live=False`, `scraper_service.py` loaded this fixture without validating whether it was a real job page or an anti-bot challenge block.
- **Proposed Remediation**:
  In `scraper_service.py`, add a challenge detection guard:
  ```python
  if "Attention Required! | Cloudflare" in html_content or "Sorry, you have been blocked" in html_content:
      logger.warning("[SCRAPER] Cloudflare challenge page detected in HTML. Bypassing invalid fixture.")
      # Invalidate fixture and trigger Playwright solve / re-fetch
  ```

---

### Anomaly 2: False Entity Extractions in NLP
- **Encountered on**: `2115360423948389981` ("Frontend Developer")
- **Extracted Company**: `"SME"` and `"Webpack, Babel"`
- **Root Cause**:
  1. The description included: *"You'll be joining us early in our mission to reinvent SME finance..."*. spaCy labeled `SME` as an `ORG`. In reality, `SME` is a common business acronym ("Small and Medium-sized Enterprises"), not a specific company name.
  2. The description included: *"Experience with Webpack, Babel, and modern build tools"*. spaCy labeled `Webpack, Babel` as an `ORG`. These are front-end build tools.
- **Impact on Search**:
  When SerpAPI searched `site:linkedin.com/in/ "Martin" "SME"`, it restricted Google queries to profiles containing the generic term `"SME"`, reducing the precision of candidate harvesting.
- **Proposed Remediation**:
  1. Add common business domain acronyms (`SME`, `B2B`, `B2C`, `SaaS`, `API`, `MVP`, `HR`, `PR`, `ROI`) to `COMPANY_STOPWORDS`.
  2. Add common developer frameworks and build tools (`Webpack`, `Babel`, `Vite`, `Next.js`, `Nuxt`, `Tailwind`, `Docker`, `Kubernetes`) to `TECH_STOPWORDS` so spaCy ORG tags matching them are discarded before querying Google X-Ray.
