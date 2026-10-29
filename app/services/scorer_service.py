from decimal import Decimal
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import rapidfuzz.fuzz as fuzz
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.candidate import Candidate
from app.services.harvester_service import PersonCandidate

logger = logging.getLogger("app.services.scorer")


DECISION_MAKER_TITLES_TOP = [
    "owner", "founder", "co-founder", "ceo", "president", "principal",
    "managing director", "chief executive", "proprietor", "cto", "chief technology officer"
]

DECISION_MAKER_TITLES_MID = [
    "director", "vp", "vice president", "head of", "partner", "general manager", "executive"
]

PROFESSIONAL_TITLES = [
    "manager", "lead", "specialist", "consultant", "architect", "engineer", "designer"
]

LOW_FIT_TITLES = [
    "student", "intern", "assistant", "retired", "junior", "trainee"
]


class LeadTarget(BaseModel):
    """Target lead attributes extracted from Upwork job & intelligence."""

    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    company_hint: Optional[str] = None
    domain_keywords: List[str] = Field(default_factory=list)


class ScoredCandidate(BaseModel):
    """Candidate profile evaluated with 4-factor scoring algorithm."""

    candidate: PersonCandidate
    score: float
    confidence: float
    tier: str
    reasons: List[str] = Field(default_factory=list)
    rank_order: int = 1
    is_primary_resolved: bool = False


class CandidateScorerService:
    """4-Factor Decision-Maker Scoring Engine with Dual Candidate Delivery."""

    def __init__(
        self,
        weight_name: float = 0.40,
        weight_location: float = 0.35,
        weight_role: float = 0.15,
        weight_company: float = 0.10,
    ):
        self.w_name = weight_name
        self.w_location = weight_location
        self.w_role = weight_role
        self.w_company = weight_company

    def evaluate_name(self, target_name: str, candidate_name: str) -> tuple[float, str]:
        t_clean = target_name.strip().lower()
        c_clean = candidate_name.strip().lower()

        t_parts = t_clean.split()
        c_parts = c_clean.split()

        # Exact match
        if t_clean == c_clean:
            return 1.0, f"Exact name match: '{candidate_name}'"

        # First name exact + initial match (e.g. 'Yaniv' vs 'Yaniv B.')
        if len(t_parts) == 1 and len(c_parts) >= 1:
            if t_parts[0] == c_parts[0]:
                return 0.90, f"Name Match (90%): '{target_name}' vs '{candidate_name}'"

        # First + Last name matches
        if len(t_parts) >= 2 and len(c_parts) >= 2:
            if t_parts[0] == c_parts[0] and t_parts[-1] == c_parts[-1]:
                return 1.0, f"Exact First & Last name match: '{candidate_name}'"
            if t_parts[0] == c_parts[0] and c_parts[-1].startswith(t_parts[-1][0]):
                return 0.95, f"Exact First Name + Last Initial match: '{candidate_name}'"

        ratio = fuzz.token_sort_ratio(t_clean, c_clean) / 100.0
        return ratio, f"Name Match ({int(ratio * 100)}%): '{target_name}' vs '{candidate_name}'"

    def evaluate_location(self, target: LeadTarget, location_text: str) -> tuple[float, str]:
        loc_lower = location_text.lower()

        if target.city and target.city.lower() in loc_lower:
            return 1.0, f"Direct city match: '{target.city}' in profile location"

        if target.state and target.state.lower() in loc_lower:
            return 0.80, f"State/Region match: '{target.state}' in profile location"

        if target.country and target.country.lower() in loc_lower:
            return 0.60, f"Country match: '{target.country}' in profile location"

        return 0.0, f"Location mismatch: Profile does not match {target.city or target.country}"

    def evaluate_role(self, headline: str) -> tuple[float, str]:
        head_lower = headline.lower()

        for low in LOW_FIT_TITLES:
            if low in head_lower:
                return 0.10, f"Low seniority / Not a decision-maker: '{low.title()}'"

        for top in DECISION_MAKER_TITLES_TOP:
            if top in head_lower:
                return 1.0, f"Executive Decision-Maker: '{top.title()}'"

        for mid in DECISION_MAKER_TITLES_MID:
            if mid in head_lower:
                return 0.80, f"Senior Leadership: '{mid.title()}'"

        for prof in PROFESSIONAL_TITLES:
            if prof in head_lower:
                return 0.50, f"Professional: '{prof.title()}'"

        return 0.30, "General professional profile"

    def evaluate_company(self, company_hint: Optional[str], candidate: PersonCandidate) -> tuple[float, str]:
        if not company_hint:
            return 0.50, "No company constraint provided"

        comp_lower = company_hint.lower()
        search_target = f"{candidate.headline} {candidate.location_text}".lower()

        if comp_lower in search_target:
            return 1.0, f"Company confirmed: '{company_hint}' found in profile"

        return 0.20, f"Company '{company_hint}' not explicitly found in snippet"

    def score_candidate(self, target: LeadTarget, candidate: PersonCandidate) -> ScoredCandidate:
        s_name, r_name = self.evaluate_name(target.name, candidate.full_name)
        s_loc, r_loc = self.evaluate_location(target, candidate.location_text)
        s_role, r_role = self.evaluate_role(candidate.headline)
        s_comp, r_comp = self.evaluate_company(target.company_hint, candidate)

        composite = (
            (s_name * self.w_name)
            + (s_loc * self.w_location)
            + (s_role * self.w_role)
            + (s_comp * self.w_company)
        )

        confidence = (s_name * 0.5) + (s_loc * 0.5)

        reasons = [r_name, r_loc, r_role, r_comp]

        if composite >= 0.80 and confidence >= 0.85:
            tier = "Tier A (High Confidence Target)"
        elif composite >= 0.65 and confidence >= 0.70:
            tier = "Tier B (Potential Match / Review Required)"
        else:
            tier = "Tier C (Low Match / Irrelevant)"

        return ScoredCandidate(
            candidate=candidate,
            score=round(composite, 4),
            confidence=round(confidence, 4),
            tier=tier,
            reasons=reasons,
        )

    def rank_and_separate(
        self,
        target: LeadTarget,
        candidates: List[PersonCandidate],
    ) -> List[ScoredCandidate]:
        """Scores and ranks all candidates, designating Rank #1 as Primary Resolved."""
        scored = [self.score_candidate(target, c) for c in candidates]
        scored.sort(key=lambda s: s.score, reverse=True)

        for idx, sc in enumerate(scored, 1):
            sc.rank_order = idx
            sc.is_primary_resolved = (idx == 1 and "Tier A" in sc.tier)

        return scored

    async def persist_candidates(
        self,
        job_id: Any,
        job_uid: str,
        scored_candidates: List[ScoredCandidate],
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Saves Stage 4 snapshot JSON and writes candidates to database."""
        snapshot_dir = settings.SNAPSHOTS_DIR / "stage4_leads"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_file = snapshot_dir / f"{job_uid}_leads.json"

        # 1. Save Stage 4 Snapshot
        payload = {
            "job_id": str(job_id),
            "job_uid": job_uid,
            "total_candidates": len(scored_candidates),
            "resolved_candidate": (
                scored_candidates[0].model_dump()
                if scored_candidates and scored_candidates[0].is_primary_resolved
                else None
            ),
            "potential_candidates": [
                s.model_dump()
                for s in scored_candidates
                if not s.is_primary_resolved
            ],
        }
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        # 2. Persist to PostgreSQL if session provided
        if session:
            logger.info(f"[SCORER] Persisting {len(scored_candidates)} scored candidate(s) to PostgreSQL for job {job_uid}...")
            # Delete old candidate rows for this job to refresh
            del_stmt = select(Candidate).filter_by(job_id=job_id)
            del_res = await session.execute(del_stmt)
            for old in del_res.scalars().all():
                await session.delete(old)

            for sc in scored_candidates:
                cand_record = Candidate(
                    job_id=job_id,
                    rank_order=sc.rank_order,
                    full_name=sc.candidate.full_name,
                    headline=sc.candidate.headline,
                    profile_location=sc.candidate.location_text,
                    linkedin_url=sc.candidate.profile_url,
                    match_score=Decimal(f"{sc.score * 100:.2f}"),
                    confidence=Decimal(f"{sc.confidence * 100:.2f}"),
                    tier=sc.tier,
                    is_primary_resolved=sc.is_primary_resolved,
                    scoring_reasons=sc.reasons,
                )
                session.add(cand_record)

            await session.commit()
            logger.info(f"[SCORER] Successfully committed {len(scored_candidates)} candidates to database.")

        return payload


scorer_service = CandidateScorerService()

