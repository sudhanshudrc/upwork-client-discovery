# Agent Brief: Upwork Client Lead Discovery and Decision-Maker Scoring Pipeline

> **How to use this document.** You are a senior Python engineer and automation architect. Read this whole brief before writing any code. Then, *before implementing*, write a short plan (architecture, risks, assumptions, open questions) and only then start building. Where this brief says **THINK**, stop and reason explicitly about the issue, and write your conclusion into `docs/DECISIONS.md`.

---

## 1. Mission (one paragraph)

Build a Python automation that (1) uses an authenticated Upwork session to search for jobs by keyword, (2) extracts every useful piece of information about each job and about the **client** who posted it (client company, location, spend history, hire rate, etc., and the client's personal name *if it is ever available*), (3) turns each client into a normalized "lead", (4) looks up **candidate real-world people** matching that lead on a professional-network data source (LinkedIn-type data: name, headline, company, location, follower/connection count, profile URL, what the person does), and (5) **scores and ranks** those candidates so a human can quickly see who is the most probable decision-maker behind each job ad. The end goal is that the user's company can contact the right person and discuss the work directly.

The final output is a ranked, explainable, reviewable list. **A human makes the final decision to contact anyone.** The system does not send messages by itself.

---

## 2. Business context (why this exists)

- The user runs or works for a software/services company and wants to find clients who are actively hiring.
- Upwork job posts are a strong *buying-intent signal*: the client has a budget and a problem right now.
- The user wants to identify who is behind the job post and what company they represent, so the company can approach them with a proposal.
- Volume is high: one keyword search can return thousands of jobs, so the pipeline must be automated, resumable, deduplicated and cheap to run.

---

## 3. Reality checks you must reason about first

**THINK about each of these and document how the design handles it.**

### 3.1 Upwork usually does NOT reveal the client's personal name
Job posts typically expose: company name (sometimes), country/city, local time, member-since date, total spent, number of jobs posted, hire rate, average hourly rate paid, payment-verified flag, and sometimes a company website or a short company description. The personal name of the person is normally hidden.

Consequences:
- The brief's original idea "search LinkedIn by the client's name" will often have **no name to search with**.
- The pipeline must therefore support **three lead types**:
  1. `NAMED` – a personal name is known (e.g. appears in the job text, a company profile, a linked website, an attached signature).
  2. `COMPANY_ONLY` – only a company name (+ location) is known. Search for *people at that company* and rank by seniority/role relevance.
  3. `ANONYMOUS` – neither name nor company. Keep the job, mark as low-confidence, and try to infer a company from the job text or company website if present. Do **not** fabricate identity.
- Never invent or guess a name. Every identity claim must carry a source and a confidence value.

### 3.2 Terms of service and platform risk
- Upwork's Terms restrict scraping/automated access and restrict taking clients off-platform to avoid fees. LinkedIn's Terms prohibit scraping. Violating these can get accounts suspended or banned and can create legal exposure.
- **Design decision (mandatory):**
  - Prefer **official or licensed access** wherever one exists: the **Upwork GraphQL API** for job search/details (if the user's account has API access), and a **licensed people/company data provider** (e.g. Apollo, People Data Labs, Hunter, LinkedIn Sales Navigator export, or similar) for professional-profile data.
  - **Do not scrape LinkedIn** (no logged-in LinkedIn browser automation, no unofficial LinkedIn scraping libraries).
  - Browser automation of Upwork is allowed **only as a fallback / prototype mode**, in a human-like, low-rate, single-session way, and the README must state the risk clearly and tell the user to check the current Terms.
  - **No evasion tooling:** no stealth plugins, no fingerprint spoofing, no proxy rotation to dodge blocks, no CAPTCHA-solving services. If a CAPTCHA, 2FA prompt, or block page appears, the program **pauses, saves state, and notifies the human**.
- Build the system behind **interfaces** (`JobSource`, `ProfileProvider`) so the user can swap between API, browser fallback, and different vendors without touching the rest of the code.

### 3.3 Privacy and data protection
- Personal data (names, profile URLs, locations) is being processed. Apply data minimization: store only fields needed for scoring and outreach, keep a `source` and `retrieved_at` on each record, provide a `purge` command to delete a lead and everything linked to it, and add a note in the README about applicable data-protection law (e.g. GDPR for EU persons, India's DPDP Act, CAN-SPAM/CASL for outreach).
- Do not store passwords. Store session state in a local file excluded by `.gitignore`.

### 3.4 Identity resolution is probabilistic
Two people called "Alex Kumar" in "Mumbai" exist. A match is never certain. The scoring system must output a **confidence score and an explanation**, never just a binary answer.

---

## 4. Required tech stack (decided; deviate only with a written reason in `docs/DECISIONS.md`)

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | Type hints everywhere, `ruff` + `mypy` clean |
| Upwork access (preferred) | Official Upwork **GraphQL API** via `httpx` + OAuth2 | Needs API key/approval from the user |
| Upwork access (fallback) | **Playwright (async)** with *persisted storage state* | User logs in **manually once**; automation reuses the saved session. Never automate password entry |
| HTML parsing | `selectolax` or `BeautifulSoup4` | Keep parsing separate from fetching so parsers are unit-testable on saved HTML |
| Data validation | `pydantic` v2 | All records are validated models |
| Storage | **SQLite** via `SQLModel` or `SQLAlchemy` | Migrations with `alembic` optional; design so Postgres is a drop-in later |
| Fuzzy matching | `rapidfuzz` | Names, company names, locations |
| Name/company normalization | `unidecode`, `nameparser`, `cleanco`-style suffix stripping, `pycountry`, `geopy` or an offline gazetteer | Handle accents, "Inc/LLC/Pvt Ltd", nicknames |
| Enrichment | Pluggable providers (see §7.5) | Ship at least one real provider adapter + one `MockProvider` + one `CSVProvider` |
| Rate limiting/retries | `tenacity` + a token-bucket limiter | Per-host limits, exponential backoff with jitter |
| CLI | `typer` | Commands listed in §7.9 |
| Config | `pydantic-settings` + `.env` + `config.yaml` | No secrets in code |
| Logging | `structlog` or `logging` with JSON option | Every external call logged with latency/status (no personal data in logs at INFO level) |
| Scheduling (optional) | `cron` or `Prefect` | Plain CLI must work without any scheduler |
| Tests | `pytest`, `pytest-asyncio`, `respx`/`vcr.py` for HTTP, saved HTML fixtures | Target ≥ 80% coverage on parsers and scoring |
| Packaging | `pyproject.toml`, `uv` or `pip-tools`, `Dockerfile` | One-command setup |

A starter skeleton exists as `lead_pipeline.py` (Playwright collector, provider interface, scoring function). Treat it as a rough reference only. Restructure it into the package layout in §13.

---

## 5. High-level architecture

```
                ┌────────────────────┐
  keywords ───► │  JobSource         │  (UpworkAPI | UpworkBrowserFallback | FixtureSource)
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │  Job Parser        │  → JobPost (validated)
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │  Client Normalizer │  → ClientLead (type: NAMED / COMPANY_ONLY / ANONYMOUS)
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │  Company Resolver  │  → domain, industry, size (via provider/website)
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │  ProfileProvider   │  → list[PersonCandidate]
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │  Matcher + Scorer  │  → ScoredCandidate (score, confidence, reasons)
                └─────────┬──────────┘
                          ▼
                ┌────────────────────┐
                │  SQLite + Exports  │  → CSV / XLSX / JSON review sheet
                └────────────────────┘
```

Each stage reads from and writes to the database so any stage can be **re-run independently** and the whole pipeline is **resumable** after a crash.

---

## 6. Data model

Create these entities (names are suggestions; keep the semantics).

```sql
-- jobs scraped/fetched from Upwork
CREATE TABLE job_post (
  id INTEGER PRIMARY KEY,
  upwork_job_id TEXT UNIQUE,          -- stable id from URL/API
  url TEXT NOT NULL,
  title TEXT, description TEXT,
  skills_json TEXT,                    -- list of skills
  budget_type TEXT,                    -- hourly | fixed
  budget_min REAL, budget_max REAL, currency TEXT,
  experience_level TEXT, duration TEXT, proposals_range TEXT,
  posted_at TEXT, fetched_at TEXT,
  search_keyword TEXT,
  raw_html_path TEXT                   -- optional pointer to saved HTML for re-parsing
);

-- the buyer side of a job post
CREATE TABLE client (
  id INTEGER PRIMARY KEY,
  job_post_id INTEGER REFERENCES job_post(id),
  lead_type TEXT CHECK (lead_type IN ('NAMED','COMPANY_ONLY','ANONYMOUS')),
  person_name TEXT,                    -- NULL unless genuinely known
  name_source TEXT,                    -- e.g. 'job_text','company_site','api'
  company_name TEXT, company_name_normalized TEXT,
  company_website TEXT, company_domain TEXT,
  country TEXT, city TEXT, timezone_hint TEXT,
  member_since TEXT, total_spent REAL, jobs_posted INTEGER,
  hire_rate REAL, avg_hourly_rate REAL, payment_verified INTEGER,
  client_quality_score REAL            -- see §9.1
);

-- possible real-world identities for a client
CREATE TABLE person_candidate (
  id INTEGER PRIMARY KEY,
  client_id INTEGER REFERENCES client(id),
  provider TEXT, provider_person_id TEXT,
  full_name TEXT, headline TEXT, current_title TEXT,
  current_company TEXT, company_domain TEXT,
  location_text TEXT, country TEXT, city TEXT,
  followers INTEGER, connections INTEGER,
  profile_url TEXT, summary TEXT,
  retrieved_at TEXT
);

-- scoring output, one row per (client, candidate)
CREATE TABLE candidate_score (
  id INTEGER PRIMARY KEY,
  person_candidate_id INTEGER REFERENCES person_candidate(id),
  score REAL, confidence REAL, rank INTEGER,
  features_json TEXT,                  -- each feature value + weight
  reasons_json TEXT,                   -- human-readable explanation lines
  scorer_version TEXT, scored_at TEXT
);

-- audit + resumability
CREATE TABLE pipeline_run (id INTEGER PRIMARY KEY, started_at TEXT, finished_at TEXT, params_json TEXT, status TEXT);
CREATE TABLE do_not_contact (id INTEGER PRIMARY KEY, value TEXT, kind TEXT, reason TEXT, added_at TEXT);
```

Constraints: dedupe jobs by `upwork_job_id`; dedupe clients across jobs by normalized company + domain (the same client often posts many jobs, so look up each unique client **once** and cache provider results to save credits).

---

## 7. Module specifications

### 7.1 Authentication / session (`sources/upwork/session.py`)
- **API mode:** OAuth2 flow, token refresh, tokens stored in an OS keyring or an encrypted local file.
- **Browser fallback mode:**
  - Command `lead-agent upwork login` opens a *headed* Chromium window. The user logs in by hand (including 2FA/CAPTCHA). The program then saves `storage_state` to `./secrets/upwork_state.json`.
  - Subsequent runs load that state. Before each run, check the session is valid (navigate to a known authenticated page; if redirected to login, stop and ask the user to log in again).
  - Never type credentials programmatically. Never attempt to bypass verification steps.

### 7.2 Job search collector (`sources/upwork/search.py`)
- Input: list of keywords + filters (experience level, budget range, posted-within-days, client history, payment verified, country include/exclude).
- Paginate through results up to `max_pages` / `max_jobs`.
- Output: `JobStub(url, title, upwork_job_id, snippet)` and then full details via §7.3.
- **Politeness requirements:** randomized delay between page loads (configurable, default 3–8 s), concurrency of 1 for browser mode, a hard cap on jobs per run and per day, and a kill-switch if error rate or block signals exceed a threshold.
- **Resilience:** selectors live in one file (`selectors.py`) keyed by semantic names, with multiple fallbacks per element (prefer `data-test` attributes and ARIA roles over brittle CSS classes). Save the raw HTML of any page that fails to parse, to `data/debug/` for later fixing. Provide a `selftest` command that runs the parsers on bundled HTML fixtures so the user can detect when Upwork changes its layout.

### 7.3 Job detail parser (`sources/upwork/parse_job.py`)
Extract, with explicit `None` when absent (never guess):
- Job: id, url, title, full description, skills, category, budget/rate, experience level, duration, project type, proposals range, interview/hire counts, posted time, "featured"/"enterprise" flags.
- Client ("About the client"): country, city, local time, company name, company website/description if shown, member-since, payment verified, rating and review count, jobs posted, hire rate, open jobs, total spent, hires, active hires, average hourly rate paid, hours billed.
- **Name hunting:** scan the job description and any visible company text for a personal name or signature (e.g. "Hi, I'm Sarah, CTO of …", "Contact: John D."). Use conservative regex + an NER model (`spaCy` small model) and record the `name_source` and a confidence. If a name is merely *possibly* present, store it as a hint, not a fact.
- Pure function: `parse_job(html: str) -> JobPost` with fixtures in `tests/fixtures/`.

### 7.4 Client normalization (`pipeline/normalize.py`)
- Clean company names (strip legal suffixes, punctuation, casing, accents) → `company_name_normalized`.
- Normalize locations to ISO country + city.
- Derive `lead_type` (NAMED / COMPANY_ONLY / ANONYMOUS).
- Compute `client_quality_score` (see §9.1) so you can prioritize which clients are worth an enrichment credit.
- Dedupe clients across jobs; link multiple jobs to the same client entity.

### 7.5 Enrichment providers (`enrichment/`)
Define:

```python
class ProfileProvider(Protocol):
    name: str
    def find_company(self, name: str, country: str | None, domain: str | None) -> CompanyInfo | None: ...
    def find_people(self, *, person_name: str | None, company: str | None,
                    domain: str | None, country: str | None, city: str | None,
                    limit: int = 10) -> list[PersonCandidate]: ...
```

Provide:
1. `MockProvider` – deterministic fake data for tests and demos.
2. `CSVProvider` – reads candidates from a CSV the user exports (e.g. from Sales Navigator or another licensed tool). This guarantees a working path with zero vendor lock-in.
3. At least one real adapter behind a feature flag (choose one from Apollo / People Data Labs / Hunter, based on the user's key), including pagination, credit accounting, and rate-limit handling.
4. A `WebsiteProvider` that fetches the client's *public* company website "About/Team/Contact" pages (respecting `robots.txt`) to extract names, titles and emails that the company itself publishes.

For each candidate capture: full name, headline, current title, current company, location, **follower count** and/or connection count if the provider supplies it, profile URL, a short "what they do" summary, and a `provider_confidence` if offered.

Rules:
- A global **cache** keyed on `(provider, query hash)` with TTL so repeated runs do not burn credits.
- A **budget guard**: `max_provider_calls_per_run` and a dry-run mode that estimates cost without calling.
- Respect `do_not_contact`.

### 7.6 Matching and scoring (`scoring/`)
See §9 for the full specification. Output must be explainable: every score ships with the list of features and plain-English reasons.

### 7.7 Storage (`db/`)
SQLAlchemy/SQLModel models, repository classes, idempotent upserts, and a `schema_version` table. Provide `lead-agent db migrate` and `lead-agent db reset`.

### 7.8 Review and export (`export/`)
- CSV/XLSX with one row per client showing: job title + URL, company, location, client quality score, lead type, **top 3 candidates** with score, confidence, title, company, followers, profile URL, and the top reasons.
- A `review` command that opens a simple terminal (Rich) or local web view (FastAPI + a single HTML page, optional) where the user can mark each candidate: `accept`, `reject`, `wrong person`, `contacted`. Store the decisions in the DB as **labeled data**, because it will be used to tune the scorer (§9.5).
- Optionally generate a *draft* outreach note per accepted candidate (templated, editable, referencing the job). **Never auto-send.**

### 7.9 CLI commands (`typer`)
```
lead-agent upwork login
lead-agent collect   --keyword "python automation" --max-jobs 200 [--source api|browser|fixtures]
lead-agent normalize
lead-agent enrich    --provider csv|apollo|pdl|mock [--dry-run] [--max-calls 100]
lead-agent score     [--scorer-version v1]
lead-agent export    --format csv|xlsx|json --min-score 0.6
lead-agent review
lead-agent run-all   --keyword ... (collect → normalize → enrich → score → export)
lead-agent selftest
lead-agent purge     --client-id N | --company "Acme"
lead-agent dnc add   --value "acme.com"
```

### 7.10 Scheduling (optional)
A cron example and an optional Prefect flow. Idempotent runs, with a lock file to prevent overlapping runs.

---

## 8. Reliability, observability and safety requirements

- **Resumable:** each stage marks records `pending | done | failed(reason)`; reruns skip `done`.
- **Retries:** transient failures retried with exponential backoff + jitter, max N attempts; permanent failures (4xx, parse errors) are logged and skipped.
- **Circuit breaker:** stop the run if more than X% of requests fail, if a CAPTCHA/403/429 pattern appears, or if daily caps are reached.
- **Human-in-the-loop interrupts:** CAPTCHA, 2FA, login expired, block page → pause, write `NEEDS_HUMAN.txt` with the reason, and exit with a distinct code.
- **Logging:** structured logs, correlation id per run, no secrets or full personal data at INFO level.
- **Config validation** at startup with clear error messages.
- **Determinism:** the scorer is deterministic given the same inputs and config version.

---

## 9. Scoring system specification (the core intellectual task)

**THINK deeply here.** The scorer answers: *"Among the people I found, who is most likely the person who posted (or controls) this Upwork job, and are they worth contacting?"* Treat it as an **entity-resolution + lead-qualification** problem and keep the two concerns separate.

### 9.1 Client quality score (is this job worth pursuing?) – range 0–1
Inputs from Upwork: payment verified, total spent (log-scaled), hire rate, jobs posted, average hourly rate paid, review rating/count, member-since age, budget size vs. the user's minimum, job freshness, competition (proposal count), and keyword/skill fit with the user's company (configurable skills list).
Example (tunable):
```
quality = 0.20*payment_verified + 0.20*norm_log(total_spent) + 0.15*hire_rate
        + 0.10*rating + 0.10*norm(avg_hourly_rate) + 0.10*budget_fit
        + 0.10*skill_fit + 0.05*freshness
```
Use quality to decide which clients get paid enrichment calls first.

### 9.2 Identity match score (is this candidate *that* client?) – range 0–1
Compute features per candidate, each in [0,1] or `None` when the input is missing:

| Feature | How |
|---|---|
| `name_match` | `rapidfuzz` token-set/ratio on normalized names, nickname table (Bob↔Robert), transliteration tolerant. **`None` if no name is known** |
| `company_match` | Fuzzy match of normalized company names + exact bonus on domain equality |
| `location_match` | Country match (strong), city match (medium), timezone consistency with Upwork local time (weak) |
| `domain_match` | Candidate's company domain equals the client's website domain (very strong) |
| `role_relevance` | Seniority/role fit for hiring: founder/owner/CEO/CTO/Head/Director/VP/Product/Engineering lead score high for small companies; for large companies, hiring managers and team leads outrank C-level; HR/recruiter is medium |
| `company_size_fit` | Small/medium company → founder-level higher; enterprise → manager-level higher |
| `activity_signal` | Recently active profile, posts about hiring/projects related to the job's skills |
| `reach` | `min(log10(followers+1)/4, 1)`; note it measures **influence, not identity**, so keep its weight small |
| `profile_completeness` | Has title, company, location, summary, photo flag |
| `topical_fit` | Headline/summary mentions skills/domain from the job (embedding or keyword overlap) |

### 9.3 Combining features
- Start with a **transparent weighted sum with missing-feature renormalization**: if a feature is `None`, exclude it and rescale the remaining weights so that missing data does not unfairly punish a candidate; lower `confidence` instead.
- Default weights for `lead_type = NAMED`: name 0.25, company 0.25, domain 0.10, location 0.10, role 0.10, topical 0.05, reach 0.05, activity 0.05, completeness 0.05.
- Default weights for `lead_type = COMPANY_ONLY`: company 0.30, domain 0.15, role 0.25, location 0.10, company_size_fit 0.05, topical 0.05, reach 0.05, activity 0.05.
- **Hard rules (veto/boost):**
  - Company mismatch AND name mismatch → score capped at 0.2.
  - Domain match + company match → floor at 0.7.
  - Candidate on `do_not_contact` → excluded.
  - Duplicate profiles (same URL or same name+company) → merged.
- **Confidence** (separate from score) = how much evidence we have: proportion of weight covered by non-missing features, number of independent agreeing signals, and margin between the top candidate and runner-up.
- Return for each candidate: `score`, `confidence`, `rank`, `features`, and `reasons` such as `"Company 'Acme Robotics' matches 'Acme Robotics Pvt Ltd' (0.96)"`, `"Located in Pune, same country as client"`, `"Title 'Co-Founder & CTO' fits a hiring decision-maker for a 12-person company"`.

### 9.4 Output tiers
- `A` (score ≥ 0.80 and confidence ≥ 0.7): strong match, ready for human review.
- `B` (0.60–0.80): plausible, needs a quick manual check.
- `C` (< 0.60): weak, show only if nothing better exists.
- If the top-2 margin is under 0.05, flag `AMBIGUOUS` so a human chooses.

### 9.5 Learning from feedback (phase 2, design for it now)
The `review` command stores accept/reject labels. Provide a `scoring/train.py` that fits a simple, interpretable model (logistic regression or gradient boosting with SHAP-style explanations) on those labels and compares it to the hand-weighted baseline on a held-out split (precision@1, precision@3, MRR). Only switch scorer versions when the learned model beats the baseline, and always keep the explanation output.

### 9.6 Evaluation
Create `tests/golden/` with ~30 hand-built cases (client + candidates + expected best match), including tricky ones: same name different company, company renamed, accents/transliteration, missing location, enterprise vs. startup, nickname vs. legal name, two founders. The scorer must pass these and the repo must include a script that prints precision@1/3 for any scorer version.

---

## 10. Configuration

`config.yaml` (example):
```yaml
search:
  keywords: ["python automation", "web scraping", "fastapi"]
  max_pages: 5
  max_jobs_per_run: 200
  max_jobs_per_day: 400
  posted_within_days: 7
  filters:
    payment_verified: true
    min_total_spent: 1000
    include_countries: []
    exclude_countries: []

politeness:
  min_delay_s: 3
  max_delay_s: 8
  concurrency: 1
  stop_on_block_signals: true

enrichment:
  provider: csv            # csv | apollo | pdl | mock
  max_calls_per_run: 100
  cache_ttl_days: 30

scoring:
  version: v1
  tier_a_min_score: 0.80
  tier_a_min_confidence: 0.70
  my_company_skills: ["python", "automation", "scraping", "api"]
  min_budget_usd: 500

privacy:
  retention_days: 90
  redact_logs: true
```
Secrets (API keys, OAuth client secrets) come from `.env` only.

---

## 11. Testing strategy

- **Unit tests:** parsers against saved HTML fixtures; normalizers (company/location/name); every scoring feature; weight renormalization with missing data.
- **Contract tests:** each `ProfileProvider` adapter against recorded responses (`vcr.py`/`respx`), never against live services in CI.
- **Integration test:** `run-all` with `FixtureSource + MockProvider` produces the expected export.
- **Golden-set evaluation** (§9.6) runs in CI and fails if precision@1 drops below the stored baseline.
- **Selector health check:** `selftest` command + a CI job that runs it on fixtures.

---

## 12. Documentation to produce

- `README.md`: purpose, setup in under 10 minutes, first run walkthrough, command reference, **clear risk/ToS section**, privacy section.
- `docs/ARCHITECTURE.md`: diagram and module responsibilities.
- `docs/DECISIONS.md`: each **THINK** item with the decision and rationale.
- `docs/SCORING.md`: formulas, weights, tiers, examples, how to tune.
- `docs/RUNBOOK.md`: what to do on login expiry, CAPTCHA, layout change, vendor quota exhausted.

---

## 13. Suggested project layout

```
lead-agent/
├─ pyproject.toml
├─ README.md
├─ .env.example
├─ config.yaml
├─ Dockerfile
├─ src/lead_agent/
│  ├─ cli.py
│  ├─ config.py
│  ├─ models.py                 # pydantic domain models
│  ├─ db/ (models.py, repo.py, migrate.py)
│  ├─ sources/
│  │  ├─ base.py                # JobSource Protocol
│  │  ├─ upwork/ (api.py, session.py, search.py, parse_job.py, selectors.py)
│  │  └─ fixtures.py
│  ├─ pipeline/ (normalize.py, dedupe.py, runner.py)
│  ├─ enrichment/ (base.py, mock.py, csv_provider.py, website.py, apollo.py, cache.py)
│  ├─ scoring/ (features.py, weights.py, scorer.py, client_quality.py, train.py, evaluate.py)
│  ├─ export/ (csv_xlsx.py, review_ui.py, outreach_draft.py)
│  └─ utils/ (ratelimit.py, retry.py, text.py, geo.py, logging.py)
├─ tests/ (unit/, integration/, golden/, fixtures/)
├─ data/ (debug/, exports/)       # git-ignored
└─ secrets/                       # git-ignored
```

---

## 14. Deliverables and acceptance criteria

**Deliverables:** the package above, passing tests, docs, a `Dockerfile`, sample fixtures, and a demo run script.

**Acceptance criteria (all must be met):**
1. `lead-agent run-all --source fixtures --provider mock` runs end-to-end offline and produces a CSV with ranked candidates, scores, confidence and reasons.
2. Parsers return `None` (not guesses) for missing fields; parser tests pass on at least 5 diverse saved job pages.
3. The pipeline is **resumable** (kill it mid-run; rerun continues without duplicates).
4. Lead types `NAMED`, `COMPANY_ONLY`, `ANONYMOUS` are all handled and covered by tests.
5. The scorer is deterministic, explainable, handles missing features by renormalizing, and passes the golden set at the documented thresholds.
6. A CAPTCHA/login-expired/block simulation causes a **safe pause** with `NEEDS_HUMAN.txt`, not a retry storm.
7. No LinkedIn scraping code exists anywhere; no stealth/CAPTCHA-bypass code exists anywhere.
8. No secrets or personal data are committed; `purge` and `dnc` commands work.
9. `ruff`, `mypy`, and `pytest` pass.
10. README states the Terms-of-Service and privacy considerations plainly.

---

## 15. Phased plan (follow this order)

1. **Phase 0 – Plan:** write the plan, assumptions, and open questions (see §16). Confirm API availability and provider choice.
2. **Phase 1 – Foundations:** project skeleton, config, models, DB, logging, fixtures, `selftest`.
3. **Phase 2 – Job ingestion:** `FixtureSource` first, then Upwork API adapter, then browser fallback; parsers + tests.
4. **Phase 3 – Normalization and dedupe:** lead typing, company/location normalization, client quality score.
5. **Phase 4 – Enrichment:** providers, cache, budget guard, website provider.
6. **Phase 5 – Scoring:** features, weights, hard rules, confidence, tiers, golden tests, evaluation script.
7. **Phase 6 – Export and review:** CSV/XLSX, review UI, feedback storage, draft outreach text.
8. **Phase 7 – Hardening:** retries, circuit breaker, runbook, Docker, CI.
9. **Phase 8 – Learning loop:** train a model on reviewed labels and compare to the baseline.

At the end of each phase, run the tests, summarize what changed, and list remaining risks.

---

## 16. Assumptions to state, and questions to ask the user (do not silently guess)

Ask or state explicit assumptions about:
1. Does the user's Upwork account have **API access** (GraphQL) approved? If not, is browser fallback acceptable given the risks?
2. Which data provider does the user already pay for or prefer (Apollo, People Data Labs, Hunter, Sales Navigator exports)? Monthly credit budget?
3. Which **keywords/skills** define a relevant job for the user's company, and what are the minimum budget and client-quality thresholds?
4. Countries or time zones to target or exclude?
5. Expected volume per day and where it will run (laptop, VPS, Docker)?
6. What does "success" look like: number of qualified leads per week, minimum precision for the top-1 candidate?
7. Which outreach channels are permitted and under what consent/legal rules in the user's jurisdiction and the target jurisdictions?
8. Should accepted leads be pushed to a CRM (HubSpot, Zoho, Google Sheets)? If yes, add a `CRMExporter` interface.

---

## 17. Edge cases the agent must explicitly think through

- The same company posts 50 jobs → one client entity, one enrichment spend.
- Agencies posting on behalf of end clients (company ≠ real buyer).
- Clients with hidden/“private” company names, or company names that are generic ("Tech Solutions").
- Non-Latin scripts, transliteration, names with prefixes/suffixes, single-name individuals.
- Companies with many similarly named employees or recent renames/acquisitions.
- Job descriptions containing emails/phone numbers or links to external sites (record them as *hints*, mark the source, and apply the privacy rules).
- Upwork layout A/B tests causing partial parse results.
- Rate-limit headers, `Retry-After`, soft-blocks that return 200 with a block page (detect by content).
- Time zones: Upwork local time shown vs. job posted time.
- Provider returns stale data (old job title) → use `retrieved_at` and a staleness penalty.
- Candidate has huge follower count but is unrelated (influencer with the same name) → reach must not outweigh identity features.

---

## 18. Non-goals (do not build)

- No automated sending of messages, connection requests or emails.
- No LinkedIn scraping or login automation.
- No CAPTCHA solving, stealth fingerprinting, residential-proxy rotation, or any attempt to defeat Upwork's or LinkedIn's anti-abuse systems.
- No attempt to extract hidden or private identity data that the platform does not display.
- No resale or bulk export of personal data beyond the user's own review needs.

---

## 19. Definition of done (what "great" looks like)

A teammate can clone the repo, run one command with fixtures to see a full demo, add their own provider key, run a keyword search within polite limits, and get a ranked, explained, reviewable list of the most probable decision-makers behind each job post, with clear confidence levels, no mystery, no hidden risk, and a feedback loop that makes the scoring better over time.
