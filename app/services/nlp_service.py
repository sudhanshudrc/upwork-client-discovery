import logging
from decimal import Decimal
import json
import re
from typing import Any, Dict, List, Optional
import spacy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("app.services.nlp")

from app.config import settings
from app.models.contract import ClientContract
from app.models.intelligence import ClientIntelligence
from app.models.job import Job
from app.schemas.intelligence import (
    DiscoveredEntityItem,
    IntelligenceExtractionResponse,
    UserConfirmationRequest,
)

# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

# Common tech stacks and general nouns to ignore when extracting company names
TECH_STOPWORDS = {
    "python", "fastapi", "react", "typescript", "javascript", "node", "nodejs",
    "aws", "gcp", "azure", "docker", "kubernetes", "sql", "postgresql", "sqlite",
    "upwork", "jira", "gemini", "openai", "chatgpt", "git", "github", "zoom",
    "shopify", "wordpress", "wix", "twilio", "api", "seo", "ui", "ux", "ai", "ml",
    "the company", "our company", "the client", "our team", "client", "freelancer",
    "english", "russian", "spanish", "german", "french", "developer", "engineer",
    "ecs", "ecr", "fargate", "lambda", "s3", "iam", "kms", "cloudwatch", "terraform",
    "genai", "rest", "graphql", "travel", "emea", "amazon", "google", "microsoft",
}

# Role titles and job descriptors to never extract as company names
ROLE_STOPWORDS = {
    "summary", "senior", "junior", "lead", "engineer", "developer", "architect",
    "backend", "frontend", "fullstack", "devops", "cloud", "application", "director",
    "manager", "specialist", "consultant", "intern", "designer", "qa", "tester",
    "head", "vp", "officer", "executive", "administrator", "analyst", "contractor",
}

AGENCY_PATTERNS = [
    r"\bour client\b",
    r"\bon behalf of\b",
    r"\bwe are an agency\b",
    r"\bdigital agency\b",
    r"\bclient of ours\b",
    r"\bwhite-?label\b",
    r"\boutsource\b",
]

NAME_REGEX = re.compile(
    r"(?:work(?:ing|ed)?\s+with|pleasure\s+with)\s+(?:Mr\.\s*)?(?!(?:this|that|these|those|the|a|an|such|our|their|his|her|my|your|him|them|someone|everyone|anyone|no\s*one|all|both|each|every|another|other|group|team)\b)([A-Z][a-z]+)|"
    r"(?:^|\.\s+)(?:Mr\.\s*)?(?!(?:It|This|That|These|Those|He|She|They|There|We|The)\b)([A-Z][a-z]+)\s+(?:is|was)\s+(?:a|an|the|such|our|great|excellent)|"
    r"(?:thanks\s+to|thank\s+you)\s+([A-Z][a-z]+)",
    re.IGNORECASE,
)

NAME_STOPWORDS = {
    "the", "a", "an", "this", "that", "these", "those",
    "client", "freelancer", "work", "job", "team", "group", "company", "agency", "crew", "organization", "folks", "people", "guys", "experts",
    "you", "him", "her", "them", "me", "us", "he", "she", "they", "we", "i", "it",
    "for", "with", "from", "to", "at", "by", "in", "on", "of",
    "great", "good", "nice", "working", "all", "very", "excellent", "project", "our", "my", "their", "his", "your",
    "best", "mr", "mrs", "ms", "dr", "russian", "english", "spanish", "german", "french",
    "someone", "everyone", "anyone", "nobody", "noone", "something", "everything", "nothing",
    "another", "other", "some", "any", "each", "every", "both", "many", "much", "more", "most", "several", "few", "one", "two", "such"
}


class UpworkNLPService:
    """Service for extracting client names and organization entities via spaCy NER and linguistic pattern mining."""

    def __init__(self):
        self.nlp = nlp

    def is_valid_person_name(self, name: Optional[str]) -> bool:
        """Validates that candidate is a genuine proper noun person name and not a pronoun/determiner."""
        if not name or len(name) < 3:
            return False
        clean = name.strip()
        if clean.lower() in NAME_STOPWORDS:
            return False
        doc = self.nlp(clean)
        for token in doc:
            if token.pos_ in ("DET", "PRON", "ADP", "CCONJ", "SCONJ", "AUX", "VERB", "ADV", "PUNCT", "SPACE"):
                return False
        return True

    def extract_client_names(
        self,
        contracts: List[Dict[str, Any]],
    ) -> List[DiscoveredEntityItem]:
        """
        Analyzes partitioned review text strictly prior to 'To freelancer:'
        using both linguistic regex anchors and spaCy NER dependency trees.
        """
        name_stats: Dict[str, Dict[str, Any]] = {}

        for c in contracts:
            review = c.get("freelancer_review_clean") or c.get("review")
            if not review or len(review) < 10:
                c["client_name_mined"] = None
                continue

            freelancer_name = c.get("freelancer_name", "")
            found_names_in_review = set()
            mined_name = None

            # 1. Regex linguistic anchors
            m = NAME_REGEX.search(review)
            if m:
                cand = next((g for g in m.groups() if g), None)
                if cand and self.is_valid_person_name(cand):
                    if not freelancer_name or cand.lower() not in freelancer_name.lower():
                        mined_name = cand.title()
                        found_names_in_review.add((mined_name, "linguistic_review_regex"))

            # 2. spaCy NER & Dependency Tree
            doc = self.nlp(review)
            for ent in doc.ents:
                if ent.label_ in ("PERSON", "NORP"):
                    name = ent.text.strip().title()
                    if not self.is_valid_person_name(name):
                        continue
                    if freelancer_name and (name.lower() in freelancer_name.lower() or freelancer_name.lower() in name.lower()):
                        continue

                    # Check dependency tree
                    dep_role = ent.root.dep_
                    if dep_role in ("nsubj", "nsubjpass", "pobj", "dobj"):
                        if not mined_name:
                            mined_name = name
                        found_names_in_review.add((name, "spacy_ner_dependency"))

            # Tag mined name on contract dictionary directly in NLP service
            c["client_name_mined"] = mined_name

            # Record stats
            for name, source in found_names_in_review:
                if name not in name_stats:
                    name_stats[name] = {
                        "name": name,
                        "source": source,
                        "count": 1,
                        "evidence": review[:140] + ("..." if len(review) > 140 else ""),
                    }
                else:
                    name_stats[name]["count"] += 1

        results = []
        for name, data in name_stats.items():
            # Consensus confidence: base 70%, +10% per extra confirming review, max 98%
            conf = min(0.70 + (data["count"] - 1) * 0.10, 0.98)
            results.append(
                DiscoveredEntityItem(
                    name=name,
                    confidence=Decimal(f"{conf * 100:.2f}"),
                    source=data["source"],
                    mention_count=data["count"],
                    supporting_context=data["evidence"],
                )
            )

        results.sort(key=lambda x: (x.mention_count, x.confidence), reverse=True)
        return results

    def extract_organization_names(
        self,
        job_description: str,
        past_titles: Optional[List[str]] = None,
        reviews: Optional[List[str]] = None,
        person_names: Optional[List[str]] = None,
    ) -> List[DiscoveredEntityItem]:
        """
        Extracts company and organization names using spaCy NER (ORG)
        from the job description, past job titles, and review text.
        """
        person_names_lower = {p.lower() for p in (person_names or [])}
        org_stats: Dict[str, Dict[str, Any]] = {}

        # 1. spaCy ORG on Job Description
        if job_description:
            doc = self.nlp(job_description)
            for ent in doc.ents:
                if ent.label_ == "ORG":
                    name = ent.text.strip()
                    words = [w.lower() for w in re.findall(r"[A-Za-z]+", name)]
                    if not words or len(name) < 3 or len(words) > 5:
                        continue
                    # Exclude job titles, seniority levels, and tech roles
                    if any(w in ROLE_STOPWORDS for w in words):
                        continue
                    # Exclude tech stack strings & cloud infrastructure
                    if any(p in name.lower() for p in (
                        "aws", "amazon", "gcp", "azure", "docker", "kubernetes", "k8s",
                        "terraform", "ecs", "ecr", "fargate", "lambda", "s3", "iam", "kms",
                        "cloudwatch", "github", "jira", "upwork", "fastapi", "react", "graphql"
                    )):
                        continue
                    if all(w in TECH_STOPWORDS or w in ROLE_STOPWORDS for w in words):
                        continue
                    if name.lower() not in TECH_STOPWORDS and name.lower() not in person_names_lower:
                        if name not in org_stats:
                            org_stats[name] = {
                                "name": name,
                                "source": "job_description_spacy_org",
                                "evidence": ent.sent.text.strip()[:140],
                                "confidence": Decimal("85.00"),
                            }

        # 2. Company pattern in past job titles (e.g. 'Tilt Web App', 'Bright Focus SEO')
        if past_titles:
            for title in past_titles:
                match = re.match(
                    r"^([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)\s+(?:App|Application|Website|Site|SEO|Bot|Platform|Portal)",
                    title,
                )
                if match:
                    cand = match.group(1).strip()
                    if cand.lower() not in TECH_STOPWORDS and cand.lower() not in person_names_lower:
                        if cand not in org_stats:
                            org_stats[cand] = {
                                "name": cand,
                                "source": "project_title_pattern",
                                "evidence": f"Past project title: '{title}'",
                                "confidence": Decimal("75.00"),
                            }

        results = [
            DiscoveredEntityItem(
                name=data["name"],
                confidence=data["confidence"],
                source=data["source"],
                mention_count=1,
                supporting_context=data["evidence"],
            )
            for data in org_stats.values()
        ]
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    def detect_agency(self, job_description: str) -> tuple[bool, Optional[str]]:
        """Detects whether the job was posted by an intermediary agency/broker."""
        if not job_description:
            return False, None

        for pat in AGENCY_PATTERNS:
            match = re.search(pat, job_description, re.IGNORECASE)
            if match:
                return True, f"Agency language detected: '{match.group(0)}'"

        return False, "Direct client posting (No agency broker language detected)"

    async def analyze_job_intelligence(
        self,
        job_id: Any,
        job_uid: str,
        job_description: str,
        contracts: List[Dict[str, Any]],
        past_titles: Optional[List[str]] = None,
        session: Optional[AsyncSession] = None,
    ) -> IntelligenceExtractionResponse:
        """
        Runs full intelligence pipeline: client name extraction, org extraction,
        agency detection, snapshot persistence, and database upsert.
        """
        # 1. Extract Client Names
        client_names = self.extract_client_names(contracts)
        suggested_client = client_names[0].name if client_names else None
        top_name_conf = (
            Decimal(str(client_names[0].confidence))
            if client_names
            else Decimal("0.00")
        )
        top_name_mentions = client_names[0].mention_count if client_names else 0
        top_name_evidence = client_names[0].supporting_context if client_names else None
        logger.info(
            f"[NLP] Person mining: {len(client_names)} candidate(s) found. Top candidate: '{suggested_client}' "
            f"(Confidence: {top_name_conf}%, Mentions: {top_name_mentions})"
        )

        # 2. Extract Company Names
        person_str_list = [c.name for c in client_names]
        org_names = self.extract_organization_names(
            job_description=job_description,
            past_titles=past_titles,
            person_names=person_str_list,
        )
        suggested_company = org_names[0].name if org_names else None
        top_company_evidence = org_names[0].supporting_context if org_names else None
        logger.info(
            f"[NLP] Organization mining: {len(org_names)} candidate(s) found. Top candidate: '{suggested_company}'"
        )

        # 3. Agency Detection
        is_agency, agency_reason = self.detect_agency(job_description)
        logger.info(f"[NLP] Agency analysis: is_agency={is_agency} ({agency_reason})")

        # 4. Save Stage 3 Snapshot JSON
        snapshot_dir = settings.SNAPSHOTS_DIR / "stage3_nlp"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_file = snapshot_dir / f"{job_uid}_intelligence.json"

        response = IntelligenceExtractionResponse(
            job_id=job_id,
            job_uid=job_uid,
            suggested_client_name=suggested_client,
            suggested_company_name=suggested_company,
            suggested_role="CTO",
            client_name_candidates=client_names,
            company_candidates=org_names,
            is_agency=is_agency,
            agency_detection_reason=agency_reason,
            approval_status="PENDING",
        )

        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(response.model_dump(mode="json"), f, indent=2)

        # 5. Persist to Database if session provided
        if session and suggested_client:
            # Sync mined client names onto client contract records
            for c in contracts:
                if c.get("id") and c.get("client_name_mined"):
                    c_stmt = select(ClientContract).filter_by(id=c["id"])
                    c_res = await session.execute(c_stmt)
                    c_row = c_res.scalars().first()
                    if c_row:
                        c_row.client_name_mined = c["client_name_mined"]

            stmt = select(ClientIntelligence).filter_by(job_id=job_id)
            res = await session.execute(stmt)
            db_intel = res.scalars().first()

            if not db_intel:
                db_intel = ClientIntelligence(
                    job_id=job_id,
                    confirmed_client_name=suggested_client,
                    confirmed_company_name=suggested_company,
                    target_role="CTO",
                    name_confidence=top_name_conf,
                    name_mentions_count=top_name_mentions,
                    name_evidence_snippet=top_name_evidence,
                    company_evidence_snippet=top_company_evidence,
                    is_agency=is_agency,
                    agency_detection_reason=agency_reason,
                    approval_status="PENDING",
                )
                session.add(db_intel)
            else:
                db_intel.confirmed_client_name = suggested_client
                db_intel.confirmed_company_name = suggested_company
                db_intel.name_confidence = top_name_conf
                db_intel.name_mentions_count = top_name_mentions

            await session.commit()

        return response

    async def confirm_intelligence(
        self,
        confirmation: UserConfirmationRequest,
        session: AsyncSession,
    ) -> ClientIntelligence:
        """
        Human-in-the-Loop Checkpoint: User confirms or edits the client person name and company name.
        """
        stmt = select(ClientIntelligence).filter_by(job_id=confirmation.job_id)
        res = await session.execute(stmt)
        db_intel = res.scalars().first()

        if not db_intel:
            db_intel = ClientIntelligence(
                job_id=confirmation.job_id,
                confirmed_client_name=confirmation.confirmed_client_name,
                confirmed_company_name=confirmation.confirmed_company_name,
                target_role=confirmation.target_role,
                approval_status="APPROVED",
            )
            session.add(db_intel)
        else:
            db_intel.confirmed_client_name = confirmation.confirmed_client_name
            db_intel.confirmed_company_name = confirmation.confirmed_company_name
            db_intel.target_role = confirmation.target_role
            db_intel.approval_status = "APPROVED"

        await session.commit()
        await session.refresh(db_intel)
        return db_intel


nlp_service = UpworkNLPService()

