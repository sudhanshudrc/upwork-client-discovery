# User Quickstart & Execution Guide: Upwork Lead Intelligence Platform

This guide provides an end-to-end operational walkthrough for running and using the platform immediately after cloning the repository. It is written from the perspective of an engineer or sales intelligence operator.

---

## 1. System Architecture Overview

The platform automates Upwork client discovery, entity extraction, and LinkedIn decision-maker harvesting:

1. **Authentication Layer (`scripts/interactive_login.py`)**: Launches a genuine Google Chrome/Brave browser via Chrome DevTools Protocol (CDP) to cleanly pass Cloudflare Turnstile and capture persistent session cookies.
2. **Database Container (`upwork_postgres`)**: PostgreSQL 16 container storing jobs, client metrics, contracts, NLP intelligence, and harvested candidates.
3. **Core API & Dashboard Container (`upwork_api`)**: FastAPI backend and responsive enterprise dark-mode UI served on `http://localhost:8000`.

---

## 2. Prerequisites

Ensure the following tools are installed on your host system:

* **Docker & Docker Compose** (v20.10+ / Compose v2+)
* **Python 3.12+** (with virtual environment support)
* **Google Chrome** or **Brave Browser** installed locally (required for Cloudflare-safe login)
* **SerpAPI Key** (optional: required for live Google X-Ray searches; pre-cached fixtures are used as fallback)

---

## 3. Step-by-Step Setup Instructions

### Step 3.1: Clone and Configure Environment

1. Clone the repository and enter the directory:
   ```bash
   git clone <repo-url> upwork-automation
   cd upwork-automation
   ```

2. Create the configuration files:
   ```bash
   # Copy environment variables
   cp .env.example .env 2>/dev/null || cat << 'EOF' > .env
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=upwork_leads
   SERPAPI_API_KEY=
   EOF

   # Ensure secrets directory exists and mirror .env
   mkdir -p secrets data/sessions data/logs
   cp .env secrets/.env
   ```

3. If you have a SerpAPI key for live LinkedIn profile scraping, add it to `.env` and `secrets/.env`:
   ```bash
   SERPAPI_API_KEY=your_serpapi_key_here
   ```

---

### Step 3.2: Run the Real-Browser Login Script

Upwork protects search and contract history behind Cloudflare Turnstile human verification. Standard automated scrapers and headless browsers are immediately flagged and blocked. 

To solve this, run the provided interactive login helper:

1. Create or activate your local Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install playwright
   python3 -m playwright install chromium
   ```

2. Run the interactive login script with your Upwork account identifier or email:
   ```bash
   python3 scripts/interactive_login.py --user your_email@domain.com
   ```

3. **What happens during this step**:
   * The script launches a genuine Google Chrome/Brave browser instance with a dedicated persistent profile (`~/.config/upwork_login_profile_<user>`) on remote debugging port `9222`.
   * A Chrome browser window opens and navigates directly to the Upwork login page (`https://www.upwork.com/ab/account-security/login`).
   * Cloudflare Turnstile verifies your genuine browser environment automatically without blocking or infinite loops.
   * Enter your Upwork email, password, and any 2FA / OTP prompts.
   * Once you are authenticated and arrive at your Upwork feed or dashboard, the script automatically:
     * Detects authenticated state.
     * Executes a live verification probe against the search feed to guarantee session validity.
     * Extracts all cookies and session storage.
     * Saves the verified session state to `data/sessions/session_<sanitized_user>.json` and `secrets/upwork_state.json`.
     * Applies cross-environment file permissions (`chmod 666`) so Docker can read and write to the session freely.
     * Gracefully closes the browser window.

---

### Step 3.3: Start the Backend and Web Interface

Start the database and application containers via Docker Compose:

```bash
docker compose up -d
```

Verify that both containers are running:
```bash
docker compose ps
```

You should see:
* `upwork_postgres`: Running and healthy on `0.0.0.0:5432`
* `upwork_api`: Running on `0.0.0.0:8000`

Inspect application startup logs:
```bash
docker compose logs -f api
```

The logs will confirm:
* Relational database tables verified and synchronized.
* Upwork Client Discovery & Decision-Maker Intelligence API online and listening on `http://0.0.0.0:8000`.

---

## 4. Using the Platform on Port 8000 (User Walkthrough)

Open your web browser and navigate to:
```
http://localhost:8000
```
(Or your local LAN address, e.g. `http://192.168.x.x:8000`).

Here is how each feature operates from a user perspective:

### 4.1 Header Bar & User Identity
* **Host & API Online Status**: Confirms connectivity to the FastAPI backend.
* **Active User Badge**: Displays the active session identity (e.g. `User: your_email@domain.com`).
* **Session Manager**: Click on the active user badge or "Switch session" to see all saved cookie profiles in `data/sessions/`. You can switch active accounts with 1 click or import session JSONs manually.
* **Export Excel Action**: Downloads the comprehensive master 46-column spreadsheet containing all discovered jobs and candidate leads across the database.
* **Docs**: Direct link to the interactive OpenAPI Swagger documentation (`/docs`).

---

### 4.2 Search Workspace

You can discover jobs using two distinct workflows:

#### Workflow A: Keyword / Title Search
1. Enter search keywords in the **Job title or keywords** field (e.g. `Senior Software Engineer`, `FastAPI Developer`, `Lead Generation`).
2. Select your job retrieval limit (5, 10, or 20 jobs).
3. Click **Search jobs**.
4. The backend connects to Upwork using your verified session cookies, pulls live listings from the feed, parses client information, and renders the job cards.

#### Workflow B: Targeted Single Job URL
1. If you already have a specific Upwork post you want to investigate, paste the URL in the **Or analyze specific job URL** field:
   ```
   https://www.upwork.com/jobs/~022115746341087253238
   ```
2. Click **Run pipeline**.
3. The system executes the full autonomous end-to-end pipeline: scraping, contract history extraction, spaCy NLP entity mining, client confirmation, and LinkedIn candidate discovery.

---

### 4.3 Discovered Job Cards & Sales Intelligence

Each retrieved job card displays enriched sales intelligence metrics:

* **Header Controls**:
  * **Job UID**: Unique identifier of the Upwork post.
  * **Pricing & Experience**: Hourly rate range or fixed price budget, plus client experience requirement tier (Entry, Intermediate, Expert).
  * **Open Upwork Post**: Direct link opening the live Upwork job post in a new tab.
  * **Copy URL**: One-click clipboard copy of the clean Upwork job link.
  * **Monospace URL Bar**: Direct visual confirmation of the canonical URL.
* **Sales Intelligence Grid**:
  * **Location & Timezone**: Client city, country, and calculated local time (e.g. `Beaverton, United States (Local: 03:45 AM PDT)`).
  * **Total Spend**: Verified financial spend of the client on Upwork.
  * **Hires & Activity**: Total hires made and count of currently active contracts.
  * **Competition Level**: Current proposals tier (e.g. `Less than 5`, `10 to 15`) and interviewing count.
  * **Account Age**: Member registration date and verification status.
  * **Project Scope**: Expected project duration and weekly time commitment.

---

### 4.4 Step 1: Scrape & Contract History Extraction

* Click **Scrape & extract contracts** (or runs automatically during autonomous runs).
* The scraper navigates to the detailed job endpoint, extracts all client feedback history, freelancer reviews, and past job contracts.
* Passes raw text to the local **spaCy NLP pipeline** to identify high-probability person names and company entities mentioned in reviews (e.g., *"Thanks to Jason for clear communication"*, *"Working with Acme Corp was great"*).

---

### 4.5 Step 2: Entity Verification & Role Confirmation

* **Evidence Quote**: Highlights the exact client feedback sentence where the name or company was found.
* **Target Client Name**: Pre-filled with the NLP-detected name (e.g. `Jason`). You can edit or refine this name.
* **Target Company Name**: Pre-filled if detected, or leave blank to search based on name and location.
* **Target Role**: Select the decision-maker role you wish to target (e.g., `CTO / Chief Technology Officer`, `CEO / Founder`, `VP of Engineering`, `Head of Product`).
* **Copy Sales Brief Button**: Generates and copies a formatted CRM lead note containing job title, client location, spend, and verified names directly to your clipboard.
* Click **Confirm & harvest LinkedIn leads**.

---

### 4.6 Step 3: Harvested LinkedIn Leads & Decision-Maker Recommendations

Once candidate discovery completes:

#### 1. Primary Resolved Decision-Maker (Tier A)
* If a candidate achieves >= 75% match confidence against the client name, location, and company, they are presented in a prominent highlighted card with their match score, headline, and direct LinkedIn profile link.

#### 2. Top 5 Recommended Candidates
* Displays up to 5 best-matching candidate profiles ranked by score:
  * Rank badge (`#1` to `#5`).
  * Candidate full name and color-coded match badge (`Score: 85% · Tier B`).
  * Current profile headline, location, and company.
  * Match evidence breakdown (e.g., `Name Match (90%) · Location Match · Title Match`).
  * Direct **View LinkedIn** action button.
* If more than 5 candidates were discovered, a collapsible drawer allows expanding the remaining results.

#### 3. Manual LinkedIn Verification Bar
Directly below the candidate recommendations, pre-configured buttons allow direct manual inspection:
* **URN Search**: Launches LinkedIn faceted search filtered by the client's resolved regional or metro GeoURN entity code (e.g. `geoUrn=["90000067"]`).
* **Name**: Direct LinkedIn search by exact client name.
* **Name + City**: Direct LinkedIn search constrained to name and city.
* **Name + Country**: Direct LinkedIn search constrained to name and country.
* **Google X-Ray**: Targeted Google search (`site:linkedin.com/in/ "{name}" "{city}"`).
* **Copy Queries**: Copies all manual verification queries and URLs to the clipboard with one click.

---

### 4.7 Step 4: Master Excel Export

* **Per-Job Export**: Click **Download Excel** on any individual job card to download an `.xlsx` workbook containing that specific job and its candidate matches.
* **Global Master Export**: Click **Export Excel** in the top navigation bar to download the complete 46-column master spreadsheet across all processed leads, pre-filtered for sales and CRM ingestion.

---

## 5. Troubleshooting & Maintenance

### 5.1 Cloudflare Turnstile Appears in Browser
If Upwork presents a Cloudflare human verification challenge when running `interactive_login.py`:
* The browser opened is genuine Google Chrome/Brave. Simply check the Turnstile checkbox manually in the browser window.
* Complete login. Once you land on `find-work` or dashboard, the script will capture the cookies automatically.

### 5.2 Permission Issues with Session Files
If you encounter `Permission denied` on `data/sessions/`:
* The application runs `chmod 666` automatically on session files.
* If needed, run on your host:
  ```bash
  chmod -R 777 data/sessions secrets
  ```

### 5.3 Resetting the Database
To wipe the database and start fresh:
```bash
docker compose down -v
docker compose up -d
```

### 5.4 Running Tests
Run the automated test suite locally:
```bash
.venv/bin/pytest tests/
```
All 27 test cases should pass cleanly.

