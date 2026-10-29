import urllib.parse
from typing import Any, Dict, List, Optional


COUNTRY_GEO_URNS: Dict[str, str] = {
    "united states": "103644278",
    "usa": "103644278",
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
    "san francisco": "90000084",
    "los angeles": "90000049",
    "chicago": "90000025",
    "london": "90009495",
    "defiance": "104689404",  # Mapped to Ohio state
    "beaverton": "90000067",  # Greater Portland-Beaverton Area
    "portland": "90000067",
    "seattle": "90000085",
    "austin": "90000090",
    "boston": "90000018",
}


class LinkedInGeoResolver:
    """Maps extracted job locations to LinkedIn native GeoURN codes and builds in-app URLs."""

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
    def generate_search_variants(
        cls,
        client_name: str,
        city: Optional[str] = None,
        country: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        name_parts = client_name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        results = []

        # 1. City / Metro GeoURN search
        city_res = cls.resolve(city=city, country=country)
        co_res = cls.resolve(country=country)

        if city_res and city_res["level"] == "metro":
            results.append({
                "strategy": f"Keywords + Metro/City GeoURN ({city_res['matched_name']})",
                "strategy_type": "urn",
                "label": f"URN: {city_res['matched_name']}",
                "geo_urn": city_res["geo_urn"],
                "url": cls.build_inapp_search_url(keywords=client_name, geo_urn=city_res["geo_urn"]),
            })
            if first_name and last_name:
                results.append({
                    "strategy": f"Structured First+Last Name + Metro GeoURN ({city_res['matched_name']})",
                    "strategy_type": "urn_name",
                    "label": f"URN: {first_name} {last_name}",
                    "geo_urn": city_res["geo_urn"],
                    "url": cls.build_inapp_search_url(first_name=first_name, last_name=last_name, geo_urn=city_res["geo_urn"]),
                })
        elif co_res:
            results.append({
                "strategy": f"Keywords + Country GeoURN ({co_res['matched_name']})",
                "strategy_type": "urn",
                "label": f"URN: {co_res['matched_name']}",
                "geo_urn": co_res["geo_urn"],
                "url": cls.build_inapp_search_url(keywords=client_name, geo_urn=co_res["geo_urn"]),
            })

        # 2. LinkedIn Search by Name only
        results.append({
            "strategy": f"LinkedIn Search: Name only ('{client_name}')",
            "strategy_type": "name",
            "label": f"Name: {client_name}",
            "geo_urn": None,
            "url": cls.build_inapp_search_url(keywords=client_name),
        })

        # 3. LinkedIn Search by Name + City
        if city:
            results.append({
                "strategy": f"LinkedIn Search: Name + City ('{client_name}' + '{city}')",
                "strategy_type": "name_city",
                "label": f"Name + City: {client_name} {city}",
                "geo_urn": None,
                "url": cls.build_inapp_search_url(keywords=f"{client_name} {city}"),
            })

        # 4. LinkedIn Search by Name + Country
        if country:
            results.append({
                "strategy": f"LinkedIn Search: Name + Country ('{client_name}' + '{country}')",
                "strategy_type": "name_country",
                "label": f"Name + Country: {client_name} {country}",
                "geo_urn": None,
                "url": cls.build_inapp_search_url(keywords=f"{client_name} {country}"),
            })

        # 5. Google X-Ray Search
        google_query = f'site:linkedin.com/in/ "{client_name}"'
        if city:
            google_query += f' "{city}"'
        elif country:
            google_query += f' "{country}"'
        results.append({
            "strategy": f"Google X-Ray Search: {google_query}",
            "strategy_type": "google_xray",
            "label": "Google X-Ray",
            "geo_urn": None,
            "url": f"https://www.google.com/search?q={urllib.parse.quote(google_query)}",
        })

        return results


geo_resolver = LinkedInGeoResolver()
