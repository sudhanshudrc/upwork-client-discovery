import urllib.parse
from typing import Any, Dict, List, Optional


COUNTRY_GEO_URNS: Dict[str, str] = {
    "united states": "103644278",
    "usa": "103644278",
    "us": "103644278",
    "u.s.": "103644278",
    "israel": "101213860",
    "united kingdom": "102257491",
    "uk": "102257491",
    "great britain": "102257491",
    "canada": "101174742",
    "australia": "101452733",
    "germany": "101282230",
    "india": "102713980",
    "france": "105015875",
    "netherlands": "102890719",
    "switzerland": "106693272",
    "spain": "105646813",
    "italy": "103350119",
    "singapore": "102454443",
    "united arab emirates": "104305776",
    "uae": "104305776",
    "saudi arabia": "100459316",
    "brazil": "106057199",
    "sweden": "105117694",
    "norway": "103819153",
    "denmark": "104514075",
    "finland": "100456013",
    "ireland": "104738515",
    "poland": "105072130",
    "mexico": "103323778",
    "argentina": "100446943",
    "south africa": "103525233",
    "new zealand": "105490917",
    "japan": "101355337",
}

US_STATE_GEO_URNS: Dict[str, str] = {
    "alabama": "104381830",
    "alaska": "102377319",
    "arizona": "103444908",
    "california": "102095887",
    "colorado": "103728639",
    "florida": "101318387",
    "georgia": "104443564",
    "illinois": "105080838",
    "massachusetts": "102824647",
    "new york": "105080838",
    "ohio": "104689404",
    "oregon": "104117822",
    "texas": "102748797",
    "washington": "103444908",
}

METRO_GEO_URNS: Dict[str, str] = {
    "winnipeg": "90008587",
    "toronto": "90008579",
    "vancouver": "90008609",
    "montreal": "90008580",
    "tel aviv": "106155005",
    "new york city": "90000070",
    "new york": "90000070",
    "nyc": "90000070",
    "san francisco": "90000084",
    "san francisco bay area": "90000084",
    "sf": "90000084",
    "san jose": "90000084",
    "los angeles": "90000049",
    "la": "90000049",
    "chicago": "90000025",
    "london": "90009495",
    "defiance": "104689404",  # Mapped to Ohio state
    "beaverton": "90000067",  # Greater Portland-Beaverton Area
    "portland": "90000067",
    "seattle": "90000085",
    "austin": "90000090",
    "boston": "90000018",
    "dallas": "90000030",
    "dallas-fort worth": "90000030",
    "houston": "90000039",
    "miami": "90000052",
    "atlanta": "90000014",
    "denver": "90000032",
    "philadelphia": "90000064",
    "san diego": "90000078",
    "phoenix": "90000065",
    "washington dc": "90000094",
    "sydney": "90008269",
    "melbourne": "90008271",
    "berlin": "106967730",
    "paris": "90009214",
    "amsterdam": "90009230",
    "bangalore": "105214831",
    "bengaluru": "105214831",
    "mumbai": "106164952",
    "delhi": "103683078",
    "dubai": "104305776",
}


class LinkedInGeoResolver:
    """Maps extracted job locations to LinkedIn native GeoURN codes and builds in-app URLs."""

    @classmethod
    def resolve_metro(cls, city: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Resolves city to Metro GeoURN if mapped, otherwise None."""
        if not city:
            return None
        c_clean = city.lower().strip()
        if c_clean in METRO_GEO_URNS:
            return {
                "level": "metro",
                "geo_urn": METRO_GEO_URNS[c_clean],
                "matched_name": city.strip().title(),
            }
        return None

    @classmethod
    def resolve_country(cls, country: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Resolves country to Country GeoURN if mapped, otherwise None."""
        if not country:
            return None
        co_clean = country.lower().strip()
        if co_clean in COUNTRY_GEO_URNS:
            return {
                "level": "country",
                "geo_urn": COUNTRY_GEO_URNS[co_clean],
                "matched_name": country.strip().title(),
            }
        return None

    @staticmethod
    def resolve(
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        if city:
            c_clean = city.lower().strip()
            if c_clean in METRO_GEO_URNS:
                return {
                    "level": "metro",
                    "geo_urn": METRO_GEO_URNS[c_clean],
                    "matched_name": f"{city.title()} ({country.title() if country else ''})".strip(),
                }

        if state:
            s_clean = state.lower().strip()
            if s_clean in US_STATE_GEO_URNS:
                return {
                    "level": "state",
                    "geo_urn": US_STATE_GEO_URNS[s_clean],
                    "matched_name": f"{state.title()}, US",
                }

        if country:
            co_clean = country.lower().strip()
            if co_clean in COUNTRY_GEO_URNS:
                return {
                    "level": "country",
                    "geo_urn": COUNTRY_GEO_URNS[co_clean],
                    "matched_name": country.title(),
                }

        return None

    @staticmethod
    def build_inapp_search_url(
        keywords: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        geo_urn: Optional[str] = None,
    ) -> str:
        base_url = "https://www.linkedin.com/search/results/people/?"
        params: Dict[str, str] = {}

        if first_name and last_name:
            params["firstName"] = first_name.strip()
            params["lastName"] = last_name.strip()
        elif keywords:
            params["keywords"] = keywords.strip()

        if geo_urn:
            params["geoUrn"] = f'["{geo_urn}"]'

        params["origin"] = "FACETED_SEARCH"
        query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        return f"{base_url}{query_string}"

    @classmethod
    def get_four_linkedin_variants(
        cls,
        client_name: str,
        city: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generates strictly the 4 LinkedIn Direct In-App URL Variants:
        1. first_last_metro_urn_url: First+Last Name + Metro GeoURN (blank if no Metro GeoURN or no last name)
        2. keywords_metro_urn_url: Keywords + Metro GeoURN (blank if no Metro GeoURN)
        3. keywords_country_urn_url: Keywords + Country GeoURN (blank if no Country GeoURN)
        4. name_location_text_url: Name + Location Text Fallback (blank if no city/country)

        Strictly no decision-maker roles injected; only client name and location.
        """
        if not client_name or not client_name.strip():
            return {
                "first_last_metro_urn_url": "",
                "keywords_metro_urn_url": "",
                "keywords_country_urn_url": "",
                "name_location_text_url": "",
            }

        c_name = client_name.strip()
        name_parts = c_name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        metro_res = cls.resolve_metro(city)
        country_res = cls.resolve_country(country)

        # 1. First+Last Name + Metro GeoURN:
        # Generated ONLY if both first and last name exist AND city has a valid Metro GeoURN
        v1_url = ""
        if first_name and last_name and metro_res:
            v1_url = cls.build_inapp_search_url(
                first_name=first_name,
                last_name=last_name,
                geo_urn=metro_res["geo_urn"],
            )

        # 2. Keywords + Metro GeoURN:
        # Generated ONLY if city has a valid Metro GeoURN
        v2_url = ""
        if metro_res:
            v2_url = cls.build_inapp_search_url(
                keywords=c_name,
                geo_urn=metro_res["geo_urn"],
            )

        # 3. Keywords + Country GeoURN:
        # Generated ONLY if country has a valid Country GeoURN
        v3_url = ""
        if country_res:
            v3_url = cls.build_inapp_search_url(
                keywords=c_name,
                geo_urn=country_res["geo_urn"],
            )

        # 4. Name + Location Text Fallback:
        # Generated ONLY if city or country text is present
        v4_url = ""
        loc_parts = []
        if city and city.strip():
            loc_parts.append(city.strip())
        if country and country.strip():
            loc_parts.append(country.strip())

        if loc_parts:
            loc_query = f"{c_name} {' '.join(loc_parts)}"
            v4_url = cls.build_inapp_search_url(keywords=loc_query)

        return {
            "first_last_metro_urn_url": v1_url,
            "keywords_metro_urn_url": v2_url,
            "keywords_country_urn_url": v3_url,
            "name_location_text_url": v4_url,
        }

    @classmethod
    def get_active_inapp_urls(
        cls,
        client_name: str,
        city: Optional[str] = None,
        country: Optional[str] = None,
    ) -> List[str]:
        """Returns only the non-blank URLs among the 4 LinkedIn variants."""
        four = cls.get_four_linkedin_variants(client_name=client_name, city=city, country=country)
        return [url for url in four.values() if url]

    @classmethod
    def generate_search_variants(
        cls,
        client_name: str,
        city: Optional[str] = None,
        country: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generates the 4 discrete search variant specifications.
        If a GeoURN or location condition is not met, the url field is left blank ("").
        No decision-maker roles (e.g. CTO/CEO) are injected.
        """
        four = cls.get_four_linkedin_variants(
            client_name=client_name,
            city=city,
            country=country,
        )

        c_name = (client_name or "").strip()
        name_parts = c_name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        metro_res = cls.resolve_metro(city)
        country_res = cls.resolve_country(country)

        metro_name = metro_res["matched_name"] if metro_res else (city.title() if city else "")
        country_name = country_res["matched_name"] if country_res else (country.title() if country else "")

        loc_parts = []
        if city and city.strip():
            loc_parts.append(city.strip())
        if country and country.strip():
            loc_parts.append(country.strip())
        loc_text = " ".join(loc_parts)

        return [
            {
                "strategy": f"Structured First+Last Name + Metro GeoURN ({metro_name})" if metro_res else "Structured First+Last Name + Metro GeoURN (No Metro URN)",
                "strategy_type": "urn_first_last_metro",
                "label": f"Metro Name: {first_name} {last_name}" if (first_name and last_name and metro_res) else "Metro Name (Blank - No Metro URN)",
                "geo_urn": metro_res["geo_urn"] if metro_res else None,
                "url": four["first_last_metro_urn_url"],
            },
            {
                "strategy": f"Keywords + Metro/City GeoURN ({metro_name})" if metro_res else "Keywords + Metro/City GeoURN (No Metro URN)",
                "strategy_type": "urn_keywords_metro",
                "label": f"Metro Keywords: {c_name}" if metro_res else "Metro Keywords (Blank - No Metro URN)",
                "geo_urn": metro_res["geo_urn"] if metro_res else None,
                "url": four["keywords_metro_urn_url"],
            },
            {
                "strategy": f"Keywords + Country GeoURN ({country_name})" if country_res else "Keywords + Country GeoURN (No Country URN)",
                "strategy_type": "urn_keywords_country",
                "label": f"Country: {country_name}" if country_res else "Country (Blank - No Country URN)",
                "geo_urn": country_res["geo_urn"] if country_res else None,
                "url": four["keywords_country_urn_url"],
            },
            {
                "strategy": f"LinkedIn Search: Name + Location Text ('{c_name}' in {loc_text})" if loc_text else "LinkedIn Search: Name + Location Text (No Location)",
                "strategy_type": "name_location_text",
                "label": f"Name + Location: {c_name} {loc_text}".strip() if loc_text else "Location Text (Blank - No Location)",
                "geo_urn": None,
                "url": four["name_location_text_url"],
            },
        ]


geo_resolver = LinkedInGeoResolver()
