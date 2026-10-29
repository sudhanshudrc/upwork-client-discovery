import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger("app.services.harvester")


class PersonCandidate(BaseModel):
    """Normalized candidate profile extracted from search engines."""

    full_name: str
    headline: str
    location_text: str
    profile_url: str
    source_query: Optional[str] = None


class SerpApiHarvesterService:
    """Executes prioritized Google X-Ray searches via SerpAPI with local MD5 response caching."""

    SERPAPI_ENDPOINT = "https://serpapi.com/search.json"

    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[Path] = None):
        self.api_key = api_key or settings.SERPAPI_API_KEY
        self.cache_dir = cache_dir or Path("playground/fixtures/serpapi_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, query: str) -> Path:
        query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
        p1 = self.cache_dir / f"serpapi_{query_hash}.json"
        if p1.exists():
            return p1
        p2 = self.cache_dir / f"{query_hash}.json"
        if p2.exists():
            return p2
        return p1


    def execute_serpapi_query(self, query: str) -> List[Dict[str, Any]]:
        """Queries SerpAPI with local disk caching."""
        cache_file = self._get_cache_path(query)
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results = data.get("organic_results", [])
                    logger.info(f"[HARVESTER] Cache HIT for query '{query}' ({len(results)} results from {cache_file.name})")
                    return results
            except Exception as e:
                logger.warning(f"[HARVESTER] Failed reading cache file {cache_file}: {e}")

        if not self.api_key:
            logger.warning("[HARVESTER] No SERPAPI_API_KEY configured. External Google X-Ray search skipped.")
            return []

        params = {
            "engine": "google",
            "q": query,
            "api_key": self.api_key,
            "num": 10,
        }

        logger.info(f"[HARVESTER] Live SerpAPI Google X-Ray query: '{query}'")
        try:
            with httpx.Client(timeout=30.0, verify=False) as client:
                resp = client.get(self.SERPAPI_ENDPOINT, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                    results = data.get("organic_results", [])
                    logger.info(f"[HARVESTER] SerpAPI returned {len(results)} organic results for query: '{query}'")
                    return results
                else:
                    logger.error(f"[HARVESTER] SerpAPI returned HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"[HARVESTER] Network/API error executing SerpAPI query '{query}': {e}", exc_info=True)

        return []

    def parse_organic_item(self, item: Dict[str, Any]) -> Optional[PersonCandidate]:
        """Parses a Google organic search result into a PersonCandidate."""
        link = item.get("link", "")
        if "linkedin.com/in/" not in link:
            return None

        # Clean canonical URL
        clean_url = link.split("?")[0].rstrip("/")
        title = item.get("title", "")
        snippet = item.get("snippet", "")

        # Extract name from title: "Yaniv B. - CTO - Tilt | LinkedIn"
        title_clean = re.sub(r"\s*[-|·]\s*LinkedIn.*$", "", title, flags=re.IGNORECASE).strip()
        parts = [p.strip() for p in re.split(r"\s+[-–—|·]\s+", title_clean) if p.strip()]

        full_name = parts[0] if parts else "Unknown Professional"
        headline = " - ".join(parts[1:]) if len(parts) > 1 else snippet[:80]
        location_text = snippet if snippet else "Location unstated"

        return PersonCandidate(
            full_name=full_name,
            headline=headline,
            location_text=location_text,
            profile_url=clean_url,
        )

    def harvest_candidates(
        self,
        name: str,
        city: Optional[str] = None,
        country: Optional[str] = None,
        company: Optional[str] = None,
    ) -> List[PersonCandidate]:
        """
        Executes prioritized Google X-Ray queries (P1, P2, P3 + Company) and deduplicates results.
        """
        seen_urls = set()
        candidates: List[PersonCandidate] = []

        queries = []

        # P1: Highest precision (Name + City + Country)
        if city and country:
            queries.append(f'site:linkedin.com/in/ "{name}" "{city}" "{country}"')

        # P2: City match
        if city:
            queries.append(f'site:linkedin.com/in/ "{name}" "{city}"')

        # P3: Company match if available
        if company:
            queries.append(f'site:linkedin.com/in/ "{name}" "{company}"')

        # P4: Country fallback
        if country:
            queries.append(f'site:linkedin.com/in/ "{name}" "{country}"')

        for q in queries:
            organic_results = self.execute_serpapi_query(q)
            for item in organic_results:
                cand = self.parse_organic_item(item)
                if cand and cand.profile_url not in seen_urls:
                    cand.source_query = q
                    seen_urls.add(cand.profile_url)
                    candidates.append(cand)

        return candidates


harvester_service = SerpApiHarvesterService()
