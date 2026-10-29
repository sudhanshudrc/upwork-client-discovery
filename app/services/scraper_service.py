import asyncio
from decimal import Decimal
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
from selectolax.lexbor import LexborHTMLParser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import logging
from app.config import settings
from app.core.rate_limiter import apply_jitter_delay
from app.models.client import Client
from app.models.contract import ClientContract
from app.models.job import Job
from app.models.search_run import SearchRun
from app.services.auth_service import auth_service

logger = logging.getLogger("app.services.scraper")


def clean_text(text: Optional[str]) -> Optional[str]:
    """Normalizes whitespace and strips text."""
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if cleaned else None


def parse_currency_amount(text: Optional[str]) -> Optional[Decimal]:
    """Parses a dollar string like '$157K' or '$80.00' into Decimal."""
    if not text:
        return None
    match = re.search(r"\$([0-9,]+(?:\.[0-9]+)?)\s*([kKmM])?", text)
    if not match:
        return None
    num_str = match.group(1).replace(",", "")
    val = float(num_str)
    multiplier = match.group(2)
    if multiplier:
        if multiplier.lower() == "k":
            val *= 1000
        elif multiplier.lower() == "m":
            val *= 1000000
    return Decimal(f"{val:.2f}")


def parse_client_location(loc_el) -> Dict[str, Optional[str]]:
    """Separates country, city, and local time from Upwork's client location component."""
    if not loc_el:
        return {"country": None, "city": None, "local_time": None}

    country = None
    city = None
    local_time = None

    strong = loc_el.css_first("strong")
    if strong:
        country = clean_text(strong.text())

    spans = [clean_text(s.text()) for s in loc_el.css("span.nowrap, span") if clean_text(s.text())]
    for s in spans:
        if re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", s, re.I):
            local_time = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", s, re.I).group(0)
        elif s != country and not city and not re.search(r"\b\d{1,2}:\d{2}\b", s):
            city = s

    return {
        "country": country,
        "city": city,
        "local_time": local_time,
    }


def parse_search_feed_html(html: str) -> List[Dict[str, Any]]:
    """Parses Upwork search feed HTML into structured job summaries."""
    tree = LexborHTMLParser(html)
    jobs = []
    seen_uids = set()

    articles = tree.css("article")
    for art in articles:
        uid = art.attributes.get("data-ev-job-uid")
        if not uid:
            link = art.css_first("a[href*='/jobs/~02']")
            if link:
                m = re.search(r"~02(\d+)", link.attributes.get("href", ""))
                if m:
                    uid = m.group(1)
        if not uid or uid in seen_uids:
            continue
        seen_uids.add(uid)

        job_url = f"https://www.upwork.com/jobs/~02{uid}"
        title_el = art.css_first("h2 a, [data-test='job-tile-title-link'], h4 a")
        title = clean_text(title_el.text()) if title_el else "Upwork Job"

        type_el = art.css_first("[data-test='job-type-label'], [data-test='is-fixed-price'], [data-test='is-hourly']")
        budget_str = clean_text(type_el.text()) if type_el else "Hourly"

        exp_el = art.css_first("[data-test='experience-level'], [data-test='contractor-tier']")
        exp_str = clean_text(exp_el.text()) if exp_el else None

        desc_el = art.css_first("[data-test='job-description-text'], .job-description, p")
        desc_str = clean_text(desc_el.text()) if desc_el else ""

        spent_el = art.css_first("[data-test='total-spent']")
        spent_str = clean_text(spent_el.text()) if spent_el else None

        loc_el = art.css_first("[data-test='client-country'], [data-qa='client-location']")
        loc_str = clean_text(loc_el.text()) if loc_el else None

        prop_el = art.css_first("[data-test='proposals'], [data-test='proposals-tier']")
        prop_str = clean_text(prop_el.text()) if prop_el else None

        pay_el = art.css_first("[data-test='payment-verification-status'], [data-test='payment-verified']")
        is_verified = bool(pay_el and "verified" in pay_el.text().lower()) if pay_el else True

        jobs.append({
            "uid": uid,
            "url": job_url,
            "title": title,
            "budget": budget_str,
            "experience_level": exp_str,
            "snippet": desc_str,
            "client_spent_snippet": spent_str,
            "client_location_snippet": loc_str,
            "proposals_tier": prop_str or "Less than 5",
            "payment_verified": is_verified,
        })
    return jobs


def parse_job_details_html(html: str, job_url: str) -> Dict[str, Any]:
    """
    Parses detailed Upwork job HTML including client stats and all expanded history
    contracts strictly partitioned prior to 'To freelancer:'.
    """
    tree = LexborHTMLParser(html)

    # 1. Job Metadata
    title_el = tree.css_first("h4.air3-card-title, h1, [data-test='job-title']")
    if not title_el:
        for h in tree.css("h4"):
            txt = clean_text(h.text())
            if txt and len(txt) > 10 and not any(k in txt.lower() for k in ["history", "client", "about", "activity"]):
                title_el = h
                break
    title = clean_text(title_el.text()) if title_el else "Upwork Job"

    desc_el = tree.css_first("[data-qa='job-description'], .job-description, [data-test='job-description-text'], .break")
    description = clean_text(desc_el.text(separator=" ")) if desc_el else ""

    # Budget & Pay Type
    price_el = tree.css_first("[data-qa='job-budget'], [data-qa='job-hourly-rate'], [data-test='job-budget']")
    budget_raw = clean_text(price_el.text()) if price_el else ""
    is_hourly = "hr" in budget_raw.lower() or "hourly" in budget_raw.lower() or "$" in budget_raw
    pay_type = "Hourly" if is_hourly else "Fixed-price"

    budget_min = None
    budget_max = None
    if "$" in budget_raw:
        rates = re.findall(r"\$([0-9,]+(?:\.[0-9]+)?)", budget_raw)
        if len(rates) == 1:
            budget_max = Decimal(rates[0].replace(",", ""))
        elif len(rates) >= 2:
            budget_min = Decimal(rates[0].replace(",", ""))
            budget_max = Decimal(rates[1].replace(",", ""))

    # Experience & Duration
    exp_el = tree.css_first("[data-qa='contractor-tier']")
    experience_level = clean_text(exp_el.text()) if exp_el else "Expert"

    duration_el = tree.css_first("[data-qa='duration']")
    project_duration = clean_text(duration_el.text()) if duration_el else None

    # Activity & Proposals
    prop_el = tree.css_first("[data-qa='proposals-tier']")
    proposals_tier = clean_text(prop_el.text()) if prop_el else "Less than 5"

    int_el = tree.css_first("[data-qa='interviewing-count']")
    interviewing = int(re.search(r"\d+", int_el.text()).group(0)) if int_el and re.search(r"\d+", int_el.text()) else 0

    inv_el = tree.css_first("[data-qa='invites-sent-count']")
    invites_sent = int(re.search(r"\d+", inv_el.text()).group(0)) if inv_el and re.search(r"\d+", inv_el.text()) else 0

    # Skills Tags
    skills = [clean_text(el.text()) for el in tree.css(".air3-token-multi-line span, [data-qa='skill']")]
    skills_tags = ", ".join([s for s in skills if s])

    # 2. Client Profile Information
    loc_el = tree.css_first("[data-qa='client-location']")
    loc_data = parse_client_location(loc_el)
    city = loc_data["city"]
    state = None
    country = loc_data["country"]
    local_time = loc_data["local_time"]

    spend_el = tree.css_first("[data-qa='client-spend']")
    spend_raw = clean_text(spend_el.text()) if spend_el else "0"
    total_spent_usd = parse_currency_amount(spend_raw) or Decimal("0.00")

    hires_el = tree.css_first("[data-qa='client-hires']")
    hires_raw = clean_text(hires_el.text()) if hires_el else ""
    total_hires = 0
    active_hires = 0
    if hires_raw:
        m_hires = re.search(r"(\d+)\s+hires?(?:,\s*(\d+)\s+active)?", hires_raw)
        if m_hires:
            total_hires = int(m_hires.group(1))
            active_hires = int(m_hires.group(2)) if m_hires.group(2) else 0

    rate_el = tree.css_first("[data-qa='client-hourly-rate']")
    avg_hourly_rate = parse_currency_amount(clean_text(rate_el.text())) if rate_el else None

    rating_el = tree.css_first(".air3-rating-value-text, .sr-only")
    client_rating = None
    if rating_el:
        m = re.search(r"([0-9.]+)", rating_el.text())
        if m:
            client_rating = Decimal(m.group(1))

    payment_node = tree.css_first("[data-qa='payment-verification-status']")
    payment_verified = "Verified" in (clean_text(payment_node.text()) if payment_node else "Verified")

    company_size_el = tree.css_first("[data-qa='client-company-profile-size']")
    company_size = clean_text(company_size_el.text()) if company_size_el else None

    industry_el = tree.css_first("[data-qa='client-company-profile-industry']")
    industry = clean_text(industry_el.text()) if industry_el else None

    member_since_el = tree.css_first("[data-qa='client-contract-date']")
    member_since = clean_text(member_since_el.text()) if member_since_el else None

    # 3. Client Recent History Contracts (Strictly Partitioned)
    contracts = []
    cards = tree.css("[data-cy='job']")
    for i, job_card in enumerate(cards):
        past_title_el = job_card.css_first("[data-cy='job-title']")
        past_title = clean_text(past_title_el.text()) if past_title_el else None

        date_el = job_card.css_first("[data-cy='date']")
        past_date = clean_text(date_el.text()) if date_el else None

        freelancer_el = job_card.css_first("a[href*='/freelancers/~']")
        freelancer_name = clean_text(freelancer_el.text()) if freelancer_el else ""

        rating_card_el = job_card.css_first(".air3-rating-value-text, .sr-only")
        rating_str = clean_text(rating_card_el.text()) if rating_card_el else None
        if rating_str and "out of" in rating_str:
            m = re.search(r"([0-9.]+)\s+out of\s+([0-9.]+)", rating_str)
            if m:
                rating_str = f"{m.group(1)} / {m.group(2)}"

        is_in_progress = bool(past_date and "present" in past_date.lower())

        # STRICT PARTITIONING RULE
        card_text = job_card.text(strip=True)
        excluded_praise = None
        if "To freelancer:" in card_text:
            parts = card_text.split("To freelancer:", 1)
            freelancer_review_raw = parts[0]
            excluded_praise = "To freelancer: " + parts[1].strip()
        else:
            freelancer_review_raw = card_text

        if is_in_progress:
            clean_review = None
            rating_str = None
        else:
            trunc_el = job_card.css_first("span.air3-truncation.ml-1x")
            if trunc_el:
                t = re.sub(r"\b(more|less)\b$", "", trunc_el.text(strip=True)).strip()
                clean_review = t if t and t.lower() != "no feedback given" else None
            else:
                clean = re.sub(r"Rating is [0-9.]+ out of [0-9.]+\s*[0-9.]*\s*(stars)?", "", freelancer_review_raw).strip()
                clean = re.sub(r"\b(more|less)\b", "", clean).strip()
                clean_review = clean if clean and len(clean) > 5 and clean.lower() != "no feedback given" else None

        contracts.append({
            "contract_index": i + 1,
            "past_title": past_title,
            "contract_status": "In progress" if is_in_progress else "Completed",
            "freelancer_name": freelancer_name,
            "rating": rating_str,
            "date_and_budget": past_date,
            "freelancer_review_clean": clean_review,
            "client_name_mined": None,  # Mined strictly by NLP Service
            "excluded_client_praise": excluded_praise,
        })

    match_uid = re.search(r"~02(\d+)", job_url)
    job_uid = match_uid.group(1) if match_uid else str(abs(hash(job_url)))

    return {
        "job_uid": job_uid,
        "job_url": job_url,
        "title": title,
        "pay_type": pay_type,
        "budget_min_usd": budget_min,
        "budget_max_usd": budget_max,
        "experience_level": experience_level,
        "project_duration": project_duration,
        "proposals_tier": proposals_tier,
        "interviewing_count": interviewing,
        "invites_sent_count": invites_sent,
        "skills_tags": skills_tags,
        "description": description,
        "client": {
            "city": city,
            "state": state,
            "country": country,
            "local_time": local_time,
            "total_spent_usd": total_spent_usd,
            "avg_hourly_rate_usd": avg_hourly_rate,
            "total_hires": total_hires,
            "active_hires": active_hires,
            "client_rating": client_rating,
            "total_reviews": len([c for c in contracts if c["contract_status"] == "Completed"]),
            "payment_verified": payment_verified,
            "company_size": company_size,
            "industry": industry,
            "member_since": member_since,
        },
        "contracts": contracts,
    }


class UpworkScraperService:
    """Production service for scraping search feeds, expanding 30+ contracts, and persisting to DB."""

    def __init__(self):
        self.auth_service = auth_service

    async def search_feed(
        self,
        query: str = "automation",
        limit: int = 15,
        force_live: bool = False,
        session: Optional[AsyncSession] = None,
        user_identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extracts the top available jobs from Upwork search feed matching the user query.
        Saves Stage 1 snapshot to disk and inserts into the database.
        """
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        snapshot_dir = settings.SNAPSHOTS_DIR / "stage1_feeds"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_file = snapshot_dir / f"{run_id}_feed.json"

        # Live Search Execution
        search_url = f"https://www.upwork.com/nx/search/jobs/?sort=recency&q={quote_plus(query)}"
        logger.info(f"[SCRAPER] Executing live feed search for query: '{query}' (user: {user_identifier or 'guest'})")

        auth_failed = False
        challenge_encountered = False

        async with async_playwright() as p:
            context = await self.auth_service.create_authenticated_context(
                p, user_identifier=user_identifier, headless=True
            )
            page = await context.new_page()

            def on_response(resp):
                nonlocal auth_failed, challenge_encountered
                if "auth.upwork.com" in resp.url and resp.status == 401:
                    auth_failed = True
                if "account-security/login" in resp.url and resp.status == 403:
                    challenge_encountered = True

            page.on("response", on_response)

            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                await context.close()
                raise RuntimeError(f"Failed to navigate to Upwork search: {str(e)}")

            try:
                await page.wait_for_selector("article[data-ev-job-uid], article, [data-test='JobTile']", timeout=12000)
                await asyncio.sleep(2)
            except Exception:
                pass

            page_title = await page.title()
            body_text = await page.inner_text("body")
            content = await page.content()
            await context.close()

            jobs = parse_search_feed_html(content)[:limit]

            # Diagnostic checks if no jobs were found
            if not jobs:
                if auth_failed:
                    raise RuntimeError(
                        f"Upwork authentication failed for '{user_identifier}' (HTTP 401 Unauthorized on oauth token). "
                        "The imported cookies are expired or missing master session credentials. "
                        "Please export fresh cookies from an active logged-in Upwork browser."
                    )
                if challenge_encountered or "Challenge" in page_title or "Cloudflare" in page_title:
                    raise RuntimeError(
                        f"Upwork security challenge encountered (Title: '{page_title}'). "
                        "Cloudflare or bot protection blocked the request. Fresh authenticated cookies are required."
                    )
                if any(k in body_text.lower() for k in ["didn't find any jobs", "no jobs found", "0 jobs found"]):
                    logger.info(f"[SCRAPER] Query '{query}' legitimately returned 0 matching jobs.")
                elif user_identifier:
                    raise RuntimeError(
                        f"No job cards could be rendered on Upwork for '{user_identifier}'. "
                        "The session cookies may be inactive or expired. Try refreshing cookies or search as guest."
                    )

        # Save Stage 1 Snapshot
        payload = {
            "run_id": run_id,
            "query": query,
            "total_extracted": len(jobs),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "jobs": jobs,
        }
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        # Sync to Database if session provided
        db_run = None
        if session:
            db_run = SearchRun(
                search_query=query,
                target_limit=limit,
                total_jobs_found=len(jobs),
                status="COMPLETED",
            )
            session.add(db_run)
            await session.commit()
            await session.refresh(db_run)

        return {
            "run_id": run_id,
            "db_run_id": str(db_run.id) if db_run else None,
            "query": query,
            "total_extracted": len(jobs),
            "snapshot_path": str(snapshot_file),
            "jobs": jobs,
        }

    async def scrape_job_details(
        self,
        job_url: str,
        expand_all_history: bool = True,
        max_pages: int = 15,
        force_live: bool = False,
        session: Optional[AsyncSession] = None,
        user_identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Deep-scrapes an Upwork job page, dynamically expands 30+ history contracts,
        applies strict review partitioning, saves Stage 2 JSON, and syncs with PostgreSQL.
        """
        match = re.search(r"~02(\d+)", job_url)
        job_uid = match.group(1) if match else str(abs(hash(job_url)))

        snapshot_dir = settings.SNAPSHOTS_DIR / "stage2_jobs"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_file = snapshot_dir / f"{job_uid}_detailed.json"
        fixture_html = Path(f"playground/fixtures/jobs/{job_uid}.html")

        html_content = ""

        # 1. Check cached HTML or detailed JSON
        if not force_live:
            if snapshot_file.exists():
                try:
                    logger.info(f"[SCRAPER] Using cached Stage 2 snapshot: {snapshot_file.name}")
                    with open(snapshot_file, "r", encoding="utf-8") as f:
                        cached_data = json.load(f)
                        if session:
                            await self.sync_job_to_db(cached_data, session)
                        return cached_data
                except Exception as e:
                    logger.warning(f"[SCRAPER] Failed to read cached snapshot ({e}), falling back to HTML")
            if fixture_html.exists():
                with open(fixture_html, "r", encoding="utf-8") as f:
                    candidate_content = f.read()
                # Check for anti-bot challenge block pages
                if "Attention Required! | Cloudflare" in candidate_content or "Sorry, you have been blocked" in candidate_content:
                    logger.warning(f"[SCRAPER] HTML fixture {fixture_html.name} is a Cloudflare anti-bot challenge page. Skipping fixture.")
                else:
                    logger.info(f"[SCRAPER] Using cached HTML fixture: {fixture_html.name}")
                    html_content = candidate_content

        # 2. Fetch live and expand history contracts
        if not html_content:
            logger.info(f"[SCRAPER] Fetching live DOM for {job_url}")
            await apply_jitter_delay()
            async with async_playwright() as p:
                context = await self.auth_service.create_authenticated_context(
                    p, user_identifier=user_identifier, headless=True
                )
                page = await context.new_page()
                await page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(2)

                if expand_all_history:
                    # Click Jobs in progress
                    try:
                        in_prog = await page.query_selector("[data-cy='jobs-in-progress-button']")
                        if in_prog and await in_prog.is_visible():
                            logger.info("[SCRAPER] Clicking 'Jobs in progress' tab")
                            await in_prog.scroll_into_view_if_needed()
                            await in_prog.click()
                            await asyncio.sleep(1.5)
                    except Exception as e:
                        logger.debug(f"[SCRAPER] 'Jobs in progress' button not present: {e}")

                    # Loop View more
                    clicks = 0
                    while clicks < max_pages:
                        try:
                            view_more = await page.query_selector("//a[contains(., 'View more')] | //button[contains(., 'View more')]")
                            if not view_more or not await view_more.is_visible():
                                break
                            await view_more.scroll_into_view_if_needed()
                            await view_more.click()
                            clicks += 1
                            logger.info(f"[SCRAPER] Clicked 'View more' ({clicks}/{max_pages})")
                            await asyncio.sleep(1.8)
                        except Exception as e:
                            logger.debug(f"[SCRAPER] Pagination loop completed after {clicks} clicks: {e}")
                            break

                html_content = await page.content()
                await context.close()

                # Cache HTML fixture
                fixture_html.parent.mkdir(parents=True, exist_ok=True)
                with open(fixture_html, "w", encoding="utf-8") as f:
                    f.write(html_content)

        # 3. Parse Detailed Job & History
        parsed = parse_job_details_html(html_content, job_url)
        logger.info(
            f"[SCRAPER] Parsed job details: '{parsed.get('title')}' with {len(parsed.get('contracts', []))} past contracts"
        )

        # Save Stage 2 Snapshot
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, default=str)

        # 4. Sync to PostgreSQL Database if session provided
        if session:
            await self.sync_job_to_db(parsed, session)

        return parsed

    async def sync_job_to_db(self, parsed: Dict[str, Any], session: AsyncSession) -> Job:
        """Upserts Client, Job, and ClientContract records into the database."""
        client_data = parsed["client"]
        job_uid = parsed["job_uid"]
        logger.info(f"[DATABASE] Synchronizing job {job_uid} and client into PostgreSQL...")

        def _to_dec(val: Any) -> Optional[Decimal]:
            if val is None or val == "":
                return None
            if isinstance(val, Decimal):
                return val
            try:
                return Decimal(str(val))
            except Exception:
                return None

        # Ensure total_spent_usd is Decimal for PostgreSQL numeric column
        raw_spent = client_data.get("total_spent_usd")
        total_spent = _to_dec(raw_spent) or Decimal("0.00")

        # Check existing client by city, country, total_spent
        query = select(Client)
        if client_data.get("city"):
            query = query.filter(Client.city == client_data.get("city"))
        if client_data.get("country"):
            query = query.filter(Client.country == client_data.get("country"))
        query = query.filter(Client.total_spent_usd == total_spent)
        res = await session.execute(query)
        db_client = res.scalars().first()

        if not db_client:
            db_client = Client(
                city=client_data.get("city"),
                state=client_data.get("state"),
                country=client_data.get("country"),
                local_time=client_data.get("local_time"),
                total_spent_usd=total_spent,
                avg_hourly_rate_usd=_to_dec(client_data.get("avg_hourly_rate_usd")),
                hire_rate_pct=_to_dec(client_data.get("hire_rate_pct")),
                total_hires=int(client_data.get("total_hires") or 0),
                active_hires=int(client_data.get("active_hires") or 0),
                client_rating=_to_dec(client_data.get("client_rating")),
                total_reviews=int(client_data.get("total_reviews") or 0),
                payment_verified=bool(client_data.get("payment_verified", True)),
                company_size=client_data.get("company_size"),
                industry=client_data.get("industry"),
                member_since=client_data.get("member_since"),
            )
            session.add(db_client)
            await session.flush()

        # Upsert Job
        job_stmt = select(Job).filter_by(job_uid=job_uid)
        job_res = await session.execute(job_stmt)
        db_job = job_res.scalars().first()

        if not db_job:
            db_job = Job(
                client_id=db_client.id,
                job_uid=job_uid,
                job_url=parsed["job_url"],
                title=parsed["title"],
                pay_type=parsed["pay_type"],
                budget_min_usd=_to_dec(parsed.get("budget_min_usd")),
                budget_max_usd=_to_dec(parsed.get("budget_max_usd")),
                experience_level=parsed.get("experience_level"),
                project_duration=parsed.get("project_duration"),
                proposals_tier=parsed.get("proposals_tier"),
                interviewing_count=int(parsed.get("interviewing_count") or 0),
                invites_sent_count=int(parsed.get("invites_sent_count") or 0),
                skills_tags=parsed.get("skills_tags"),
                description=parsed.get("description", ""),
            )
            session.add(db_job)
            await session.flush()

        # Sync Contract History (Strict Partitioning)
        # Delete old contracts for this client to refresh
        for c in parsed.get("contracts", []):
            contract_obj = ClientContract(
                client_id=db_client.id,
                contract_index=c["contract_index"],
                past_title=c.get("past_title"),
                contract_status=c["contract_status"],
                freelancer_name=c.get("freelancer_name"),
                rating=c.get("rating"),
                date_and_budget=c.get("date_and_budget"),
                freelancer_review_clean=c.get("freelancer_review_clean"),
                client_name_mined=c.get("client_name_mined"),
                excluded_client_praise=c.get("excluded_client_praise"),
            )
            session.add(contract_obj)

        await session.commit()
        # Eager load client relationship to avoid MissingGreenlet in async contexts
        load_stmt = select(Job).filter_by(id=db_job.id).options(selectinload(Job.client))
        load_res = await session.execute(load_stmt)
        return load_res.scalars().one()


scraper_service = UpworkScraperService()
