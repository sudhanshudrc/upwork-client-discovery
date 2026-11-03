import io
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.client import Client
from app.models.intelligence import ClientIntelligence
from app.models.job import Job
from app.models.search_run import SearchRun

logger = logging.getLogger("app.services.excel")


# Palette Definitions
TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="1F4E78")
SUBTITLE_FONT = Font(name="Calibri", size=10, italic=True, color="595959")
WHITE_BOLD_FONT = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
REGULAR_FONT = Font(name="Calibri", size=10)
BOLD_FONT = Font(name="Calibri", size=10, bold=True)
LINK_FONT = Font(name="Calibri", size=10, color="0563C1", underline="single")

NAVY_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")

# Borders
THIN_BORDER_SIDE = Side(border_style="thin", color="D9D9D9")
GRID_BORDER = Border(
    left=THIN_BORDER_SIDE, right=THIN_BORDER_SIDE, top=THIN_BORDER_SIDE, bottom=THIN_BORDER_SIDE
)


# Master 34 Column Definitions in exact user-requested sequence
COLUMNS_SPEC = [
    {"id": "job_title", "title": "Job Title", "width": 32, "type": "text"},
    {"id": "job_url", "title": "Job URL", "width": 46, "type": "url"},
    {"id": "posted_at_relative", "title": "Posted Relative", "width": 18, "type": "text"},
    {"id": "pay_type", "title": "Pay Type", "width": 14, "type": "text"},
    {"id": "budget_min_usd", "title": "Budget Min ($)", "width": 15, "type": "currency"},
    {"id": "budget_max_usd", "title": "Budget Max ($)", "width": 15, "type": "currency"},
    {"id": "project_duration", "title": "Duration", "width": 18, "type": "text"},
    {"id": "experience_level", "title": "Experience Level", "width": 16, "type": "text"},
    {"id": "proposals_tier", "title": "Proposals Tier", "width": 16, "type": "text"},
    {"id": "interviewing_count", "title": "Interviewing", "width": 14, "type": "int"},
    {"id": "invites_sent_count", "title": "Invites Sent", "width": 14, "type": "int"},
    {"id": "unanswered_invites", "title": "Unanswered Invites", "width": 18, "type": "int"},
    {"id": "hours_per_week", "title": "hours_per_week", "width": 16, "type": "text"},
    {"id": "client_local_time_activity", "title": "Client Local Time", "width": 20, "type": "text"},
    {"id": "payment_verified", "title": "Payment Verified", "width": 16, "type": "bool"},
    {"id": "client_rating", "title": "Client Rating", "width": 14, "type": "decimal"},
    {"id": "client_reviews_count", "title": "Total Reviews", "width": 14, "type": "int"},
    {"id": "client_total_spent_usd", "title": "Total Spent ($)", "width": 16, "type": "currency"},
    {"id": "client_hire_rate_pct", "title": "Hire Rate (%)", "width": 14, "type": "pct"},
    {"id": "client_total_hires", "title": "Total Hires", "width": 13, "type": "int"},
    {"id": "client_active_hires", "title": "Active Hires", "width": 13, "type": "int"},
    {"id": "client_avg_hourly_rate", "title": "Avg Hourly ($)", "width": 15, "type": "currency"},
    {"id": "client_city", "title": "Client City", "width": 16, "type": "text"},
    {"id": "client_country", "title": "Client Country", "width": 16, "type": "text"},
    {"id": "timezone_local_time", "title": "Timezone / Local Time", "width": 22, "type": "text"},
    {"id": "client_member_since", "title": "Member Since", "width": 16, "type": "text"},
    {"id": "client_name", "title": "Client Name", "width": 24, "type": "text"},
    {"id": "client_name_confidence", "title": "Name Conf (%)", "width": 14, "type": "pct"},
    {"id": "client_name_mentions", "title": "Name Mentions", "width": 15, "type": "int"},
    {"id": "client_name_evidence", "title": "Name Evidence Snippet", "width": 38, "type": "text"},
    {"id": "company_name", "title": "Company Name", "width": 20, "type": "text"},
    {"id": "company_evidence", "title": "Company Evidence Snippet", "width": 38, "type": "text"},
    {"id": "is_agency", "title": "Is Agency", "width": 13, "type": "bool"},
    {"id": "job_description", "title": "Full Job Description", "width": 55, "type": "text"},
]


def format_client_name(intel: Optional[ClientIntelligence]) -> str:
    """
    Formats mined client name according to specification:
    - If multiple names exist, returns JSON list string e.g. ["client1", "client2"]
    - If single name exists, returns the string directly e.g. "client1"
    - If no name exists, returns empty string.
    """
    if not intel or not intel.confirmed_client_name:
        return ""

    raw = intel.confirmed_client_name.strip()
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                clean_list = [str(p).strip() for p in parsed if str(p).strip()]
                if len(clean_list) > 1:
                    return json.dumps(clean_list)
                elif len(clean_list) == 1:
                    return clean_list[0]
                return ""
        except Exception:
            pass

    names = [n.strip() for n in raw.split(",") if n.strip()]
    if len(names) > 1:
        return json.dumps(names)
    elif len(names) == 1:
        return names[0]
    return ""


def generate_sales_pitch_hook(
    client_name: Optional[str],
    company_name: Optional[str],
    job_title: str,
    skills_tags: Optional[str],
) -> str:
    """Generates an executive-ready opening sales pitch hook tailored to client, company, and project."""
    top_skills = [s.strip() for s in (skills_tags or "").split(",") if s.strip()][:3]
    skills_phrase = f"in {', '.join(top_skills)}" if top_skills else "in your required technology stack"

    if client_name and client_name != "Client" and company_name:
        return (
            f"Hi {client_name}, saw your {job_title} opening for {company_name}. "
            f"With proven production experience {skills_phrase}, I can deliver immediate impact and streamline execution."
        )
    elif client_name and client_name != "Client":
        return (
            f"Hi {client_name}, I came across your {job_title} posting. "
            f"Having delivered multiple high-reliability solutions {skills_phrase}, I can help you hit the ground running."
        )
    elif company_name:
        return (
            f"Hi there, saw your {job_title} project for {company_name}. "
            f"With strong expertise {skills_phrase}, I would welcome the opportunity to support your technical roadmap."
        )
    return (
        f"Hi, I saw your {job_title} posting. "
        f"With hands-on expertise {skills_phrase}, I can deliver high-quality, maintainable results on schedule."
    )


class ExcelExportService:
    """Enterprise Master Excel Exporter with strictly 34 Columns and JSON Multi-Name Formatting."""

    @staticmethod
    def build_row_data(job: Job) -> Dict[str, Any]:
        """Maps Job, Client, and Intelligence models into the 34-column schema dictionary."""
        client: Optional[Client] = job.client
        intel: Optional[ClientIntelligence] = job.intelligence

        posted_rel = "Recently"
        if job.posted_at:
            posted_rel = job.posted_at.strftime("%Y-%m-%d %H:%M")
        elif getattr(job, "_posted_time_raw", None):
            posted_rel = str(getattr(job, "_posted_time_raw"))

        client_name_val = format_client_name(intel)

        return {
            "job_title": job.title or "",
            "job_url": job.job_url or "",
            "posted_at_relative": posted_rel,
            "pay_type": job.pay_type or "",
            "budget_min_usd": float(job.budget_min_usd) if job.budget_min_usd is not None else None,
            "budget_max_usd": float(job.budget_max_usd) if job.budget_max_usd is not None else None,
            "project_duration": job.project_duration or "",
            "experience_level": job.experience_level or "",
            "proposals_tier": job.proposals_tier or "",
            "interviewing_count": job.interviewing_count if job.interviewing_count is not None else 0,
            "invites_sent_count": job.invites_sent_count if job.invites_sent_count is not None else 0,
            "unanswered_invites": job.unanswered_invites if job.unanswered_invites is not None else 0,
            "hours_per_week": job.hours_per_week or "",
            "client_local_time_activity": client.local_time if client and client.local_time else "",
            "payment_verified": client.payment_verified if client else False,
            "client_rating": float(client.client_rating) if client and client.client_rating is not None else None,
            "client_reviews_count": client.total_reviews if client else 0,
            "client_total_spent_usd": float(client.total_spent_usd) if client and client.total_spent_usd is not None else 0.0,
            "client_hire_rate_pct": float(client.hire_rate_pct) if client and client.hire_rate_pct is not None else None,
            "client_total_hires": client.total_hires if client else 0,
            "client_active_hires": client.active_hires if client else 0,
            "client_avg_hourly_rate": float(client.avg_hourly_rate_usd) if client and client.avg_hourly_rate_usd is not None else None,
            "client_city": client.city if client else "",
            "client_country": client.country if client else "",
            "timezone_local_time": client.local_time if client else "",
            "client_member_since": client.member_since if client else "",
            "client_name": client_name_val,
            "client_name_confidence": float(intel.name_confidence) if intel and intel.name_confidence is not None else None,
            "client_name_mentions": intel.name_mentions_count if intel else 0,
            "client_name_evidence": intel.name_evidence_snippet if intel else "",
            "company_name": intel.confirmed_company_name if intel else "",
            "company_evidence": intel.company_evidence_snippet if intel else "",
            "is_agency": intel.is_agency if intel else False,
            "job_description": job.description or "",
        }

    def generate_leads_workbook(
        self,
        jobs: List[Job],
        output_path: Optional[Path] = None,
        only_primary: bool = False,
    ) -> Path:
        """
        Creates an executive-ready Excel workbook with strictly 34 master columns.
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Job Leads & Intelligence"
        ws.views.sheetView[0].showGridLines = True

        # 1. Title Block (Row 1) - merged across 34 columns (A1:AH1)
        ws.merge_cells("A1:AH1")
        title_cell = ws["A1"]
        title_cell.value = "Upwork Job Leads & Client Intelligence Master Export"
        title_cell.font = TITLE_FONT
        title_cell.alignment = Alignment(vertical="center", indent=1)
        ws.row_dimensions[1].height = 34

        # 2. Subtitle / Metadata Block (Row 2) - merged across 34 columns (A2:AH2)
        ws.merge_cells("A2:AH2")
        sub_cell = ws["A2"]
        sub_cell.value = (
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | "
            f"Total Jobs Exported: {len(jobs)} | "
            "Master 34-Column Intelligence Specification"
        )
        sub_cell.font = SUBTITLE_FONT
        sub_cell.alignment = Alignment(vertical="center", indent=1)
        ws.row_dimensions[2].height = 20

        # 3. Column Headers (Row 3)
        ws.row_dimensions[3].height = 28
        for col_idx, col_spec in enumerate(COLUMNS_SPEC, 1):
            cell = ws.cell(row=3, column=col_idx, value=col_spec["title"])
            cell.fill = NAVY_FILL
            cell.font = WHITE_BOLD_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = GRID_BORDER

        # 4. Data Rows (Row 4+) - Exactly 1 row per job
        current_row = 4
        for job in jobs:
            row_dict = self.build_row_data(job)
            ws.row_dimensions[current_row].height = 24

            for col_idx, col_spec in enumerate(COLUMNS_SPEC, 1):
                val = row_dict.get(col_spec["id"])
                cell = ws.cell(row=current_row, column=col_idx)
                cell.border = GRID_BORDER

                col_type = col_spec["type"]
                align = Alignment(vertical="center")

                # Hyperlink Columns (Raw Clickable URLs)
                if col_type == "url":
                    url_str = str(val or "")
                    if url_str.startswith("http"):
                        cell.value = url_str
                        cell.hyperlink = url_str
                        cell.font = LINK_FONT
                    else:
                        cell.value = url_str
                        cell.font = REGULAR_FONT
                    align = Alignment(vertical="center")

                # Percentage Columns
                elif col_type == "pct":
                    align = Alignment(horizontal="center", vertical="center")
                    if val is not None and str(val).strip() != "":
                        try:
                            cell.value = f"{float(val):.1f}%"
                            cell.font = BOLD_FONT
                        except Exception:
                            cell.value = str(val)
                            cell.font = REGULAR_FONT
                    else:
                        cell.value = ""
                        cell.font = REGULAR_FONT

                # Currency Columns
                elif col_type == "currency":
                    align = Alignment(horizontal="right", vertical="center")
                    if val is not None and str(val).strip() != "":
                        try:
                            cell.value = f"${float(val):,.2f}"
                            cell.font = REGULAR_FONT
                        except Exception:
                            cell.value = str(val)
                            cell.font = REGULAR_FONT
                    else:
                        cell.value = ""
                        cell.font = REGULAR_FONT

                # Integer / Decimal Columns
                elif col_type in ("int", "decimal"):
                    align = Alignment(horizontal="center", vertical="center")
                    cell.value = val if val is not None else ""
                    cell.font = REGULAR_FONT

                # Boolean Columns
                elif col_type == "bool":
                    align = Alignment(horizontal="center", vertical="center")
                    cell.value = "TRUE" if val else "FALSE"
                    cell.font = BOLD_FONT if val else REGULAR_FONT

                # Default Text
                else:
                    cell.value = str(val) if val is not None else ""
                    cell.font = REGULAR_FONT

                cell.alignment = align

            current_row += 1

        # 5. Auto-fit column widths using spec dimensions
        for col_idx, col_spec in enumerate(COLUMNS_SPEC, 1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = col_spec["width"]

        # 6. Safe File Saving (with Fallback for Locked Files)
        target_path = output_path or (settings.EXPORTS_DIR / "leads_master.xlsx")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            wb.save(target_path)
            return target_path
        except PermissionError:
            fallback = target_path.parent / f"{target_path.stem}_new{target_path.suffix}"
            wb.save(fallback)
            return fallback

    async def export_from_db(
        self,
        session: AsyncSession,
        job_uid: Optional[str] = None,
        query: Optional[str] = None,
        run_id: Optional[str] = None,
        completed_only: bool = False,
        min_spend: Optional[Decimal] = None,
        tier: Optional[str] = None,
        country: Optional[str] = None,
        only_primary: bool = False,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Dynamically filters database jobs and generates the Master 34-Column Excel Workbook.
        When query or run_id is provided, exports strictly the exact jobs from that active search run
        (e.g. 3, 5, or 10 jobs) in their current search sequence, merging full DB details for expanded jobs.
        """
        clean_q = f"%{query.strip()}%" if query and query.strip() else None
        jobs: List[Job] = []

        # Case 1: Single job export
        if job_uid:
            stmt = (
                select(Job)
                .options(
                    selectinload(Job.client),
                    selectinload(Job.intelligence),
                    selectinload(Job.candidates),
                )
                .filter(Job.job_uid == job_uid)
            )
            res = await session.execute(stmt)
            single_j = res.scalars().first()
            if single_j:
                jobs.append(single_j)

        # Case 2: Active search run export (exports strictly the N jobs from the active search)
        elif clean_q or run_id:
            sr_stmt = select(SearchRun)
            if run_id:
                try:
                    sr_stmt = sr_stmt.filter(SearchRun.id == uuid.UUID(run_id))
                except Exception:
                    sr_stmt = sr_stmt.filter(SearchRun.id == run_id)
            elif clean_q:
                sr_stmt = sr_stmt.filter(SearchRun.search_query.ilike(clean_q)).order_by(SearchRun.created_at.desc())

            sr_res = await session.execute(sr_stmt)
            target_run = sr_res.scalars().first()

            if target_run and target_run.raw_jobs_payload:
                run_job_uids = [j.get("uid") for j in target_run.raw_jobs_payload if j.get("uid")]

                db_jobs_stmt = (
                    select(Job)
                    .options(
                        selectinload(Job.client),
                        selectinload(Job.intelligence),
                        selectinload(Job.candidates),
                    )
                    .filter(Job.job_uid.in_(run_job_uids))
                )
                db_res = await session.execute(db_jobs_stmt)
                db_jobs_map = {j.job_uid: j for j in db_res.scalars().all()}

                for raw_j in target_run.raw_jobs_payload:
                    ruid = raw_j.get("uid")
                    if not ruid:
                        continue

                    budget_str = raw_j.get("budget") or ""
                    b_min = None
                    b_max = None
                    if "$" in budget_str:
                        b_matches = re.findall(r"\$([0-9,]+(?:\.[0-9]+)?)", budget_str)
                        if len(b_matches) == 1:
                            val = Decimal(b_matches[0].replace(",", ""))
                            b_min = val
                            b_max = val
                        elif len(b_matches) >= 2:
                            b_min = Decimal(b_matches[0].replace(",", ""))
                            b_max = Decimal(b_matches[1].replace(",", ""))

                    hpw = raw_j.get("hours_per_week")
                    dur = raw_j.get("duration")
                    if not hpw and dur:
                        hpw_candidate = re.search(
                            r"((?:less than|more than|\d+\+?|\d+-\d+)?\s*(?:hrs/week|hrs/wk|hours/week|hours per week|hrs))",
                            dur,
                            re.IGNORECASE,
                        )
                        if hpw_candidate:
                            hpw = hpw_candidate.group(1).strip()
                            dur = re.sub(re.escape(hpw_candidate.group(0)), "", dur).strip(" ,•-") or None

                    if ruid in db_jobs_map:
                        db_j = db_jobs_map[ruid]
                        if db_j.budget_min_usd is None and b_min is not None:
                            db_j.budget_min_usd = b_min
                        if db_j.budget_max_usd is None and b_max is not None:
                            db_j.budget_max_usd = b_max
                        if not db_j.hours_per_week and hpw:
                            db_j.hours_per_week = hpw
                        if not db_j.project_duration and dur:
                            db_j.project_duration = dur
                        if db_j.client and db_j.client.client_rating is None and raw_j.get("client_rating"):
                            try:
                                db_j.client.client_rating = Decimal(str(raw_j["client_rating"]))
                            except Exception:
                                pass
                        jobs.append(db_j)
                    else:
                        client_rating_dec = None
                        if raw_j.get("client_rating"):
                            try:
                                client_rating_dec = Decimal(str(raw_j["client_rating"]))
                            except Exception:
                                pass

                        spent_dec = Decimal("0.00")
                        spent_str = raw_j.get("client_spent") or ""
                        if spent_str:
                            m_spent = re.search(r"\$([0-9,]+(?:\.[0-9]+)?)", spent_str)
                            if m_spent:
                                spent_dec = Decimal(m_spent.group(1).replace(",", ""))

                        synthetic_client = Client(
                            payment_verified=raw_j.get("payment_verified", False),
                            country=raw_j.get("client_location") or raw_j.get("location"),
                            client_rating=client_rating_dec,
                            total_spent_usd=spent_dec,
                        )

                        synthetic_job = Job(
                            client=synthetic_client,
                            job_uid=ruid,
                            job_url=raw_j.get("url") or f"https://www.upwork.com/jobs/~{ruid}",
                            title=raw_j.get("title") or "Untitled Job",
                            pay_type=raw_j.get("job_type") or raw_j.get("pay_type") or "Hourly",
                            budget_min_usd=b_min,
                            budget_max_usd=b_max,
                            experience_level=raw_j.get("experience_level"),
                            project_duration=dur,
                            hours_per_week=hpw,
                            proposals_tier=raw_j.get("proposals_tier"),
                            description=raw_j.get("snippet") or raw_j.get("description") or "",
                        )
                        if raw_j.get("posted_time"):
                            setattr(synthetic_job, "_posted_time_raw", raw_j.get("posted_time"))
                        jobs.append(synthetic_job)
            else:
                stmt = (
                    select(Job)
                    .options(
                        selectinload(Job.client),
                        selectinload(Job.intelligence),
                        selectinload(Job.candidates),
                    )
                    .outerjoin(Job.search_run)
                    .filter(
                        or_(
                            SearchRun.search_query.ilike(clean_q),
                            Job.title.ilike(clean_q),
                            Job.skills_tags.ilike(clean_q),
                        )
                    )
                    .order_by(Job.created_at.desc())
                )
                res = await session.execute(stmt)
                jobs = list(res.scalars().all())

        # Case 3: Bulk export all jobs in PostgreSQL
        else:
            stmt = (
                select(Job)
                .options(
                    selectinload(Job.client),
                    selectinload(Job.intelligence),
                    selectinload(Job.candidates),
                )
                .order_by(Job.created_at.desc())
            )
            if completed_only:
                stmt = stmt.filter(or_(Job.candidates.any(), Job.intelligence.has()))
            if country:
                stmt = stmt.join(Job.client).filter(Client.country.ilike(f"%{country}%"))
            if min_spend is not None:
                stmt = stmt.join(Job.client).filter(Client.total_spent_usd >= min_spend)
            res = await session.execute(stmt)
            jobs = list(res.scalars().all())

        # Optional filter by candidate tier
        if tier:
            filtered_jobs = []
            for j in jobs:
                has_tier = any(tier.lower() in (c.tier or "").lower() for c in j.candidates)
                if has_tier:
                    filtered_jobs.append(j)
            jobs = filtered_jobs

        target_path = output_path
        if not target_path and query and query.strip():
            clean_name = re.sub(r"[^a-zA-Z0-9_-]", "_", query.strip().lower())
            target_path = settings.EXPORTS_DIR / f"leads_{clean_name}.xlsx"

        logger.info(f"[EXCEL] Generating leads workbook for {len(jobs)} jobs (query: '{query or 'all'}', output: {target_path or 'default'})...")
        path = self.generate_leads_workbook(
            jobs=jobs,
            output_path=target_path,
            only_primary=only_primary,
        )
        logger.info(f"[EXCEL] Successfully generated sales-ready Excel workbook: {path}")
        return path


excel_export_service = ExcelExportService()
