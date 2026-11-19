from __future__ import annotations

import logging
import os
import re
import sys
from typing import Optional, Tuple
import httpx

from academic_paper_mcp.deduplication import normalize_arxiv_id, normalize_doi

logger = logging.getLogger("academic_paper_mcp.pdf_resolver")

EZPROXY_PREFIX = os.getenv("EZPROXY_PREFIX", "https://login.unslib.idm.oclc.org/login?url=")
DEFAULT_EMAIL = os.getenv("UNPAYWALL_EMAIL") or os.getenv("OPENALEX_EMAIL") or "dev@dpm.web.id"


def build_ezproxy_url(doi: str) -> str:
    """Build pre-authenticated institutional EZproxy URL for paywalled DOIs.
    
    UNS Library EZproxy uses OCLC IDM authentication:
    Format: https://login.unslib.idm.oclc.org/login?url=https://doi.org/<DOI>
    """
    clean_doi = normalize_doi(doi) or doi
    clean_prefix = EZPROXY_PREFIX.strip()
    if not clean_prefix.endswith("="):
        clean_prefix += "?url=" if "?" not in clean_prefix else "&url="
    return f"{clean_prefix}https://doi.org/{clean_doi}"


async def resolve_doi_to_pdf(
    doi: str,
    client: Optional[httpx.AsyncClient] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a DOI to a direct open-access PDF URL using Unpaywall, OpenAlex, and Europe PMC.
    
    Returns:
        Tuple of (pdf_url, source_engine) or (None, None) if strictly paywalled.
    """
    clean_doi = normalize_doi(doi)
    if not clean_doi:
        return None, None

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
        should_close = True

    try:
        # 1. Query Unpaywall API (Official Gold/Green Open Access repository aggregator)
        try:
            unpaywall_url = f"https://api.unpaywall.org/v2/{clean_doi}"
            params = {"email": DEFAULT_EMAIL}
            resp = await client.get(unpaywall_url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("is_oa"):
                    best_oa = data.get("best_oa_location") or {}
                    if best_oa.get("url_for_pdf"):
                        return best_oa["url_for_pdf"], "Unpaywall"

                    # Check other locations
                    for loc in data.get("oa_locations") or []:
                        if isinstance(loc, dict) and loc.get("url_for_pdf"):
                            return loc["url_for_pdf"], "Unpaywall"
        except Exception as e:
            logger.warning("Unpaywall resolution failed for %s: %s", clean_doi, e)

        # 2. Query OpenAlex Works API
        try:
            openalex_url = f"https://api.openalex.org/works/https://doi.org/{clean_doi}"
            resp = await client.get(openalex_url)
            if resp.status_code == 200:
                data = resp.json()
                primary_loc = data.get("primary_location") or {}
                if primary_loc.get("pdf_url"):
                    return primary_loc["pdf_url"], "OpenAlex"

                best_oa = data.get("best_oa_location") or {}
                if best_oa.get("pdf_url"):
                    return best_oa["pdf_url"], "OpenAlex"

                oa_info = data.get("open_access") or {}
                oa_url = oa_info.get("oa_url")
                if oa_url and oa_url.lower().endswith(".pdf"):
                    return oa_url, "OpenAlex"
        except Exception as e:
            logger.warning("OpenAlex resolution failed for %s: %s", clean_doi, e)

        # 3. Query Europe PMC API
        try:
            epmc_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            params = {
                "query": f'DOI:"{clean_doi}"',
                "format": "json",
                "resultType": "core",
            }
            resp = await client.get(epmc_url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("resultList", {}).get("result", [])
                if results:
                    first = results[0]
                    # Check fulltext urls
                    for url_item in first.get("fullTextUrlList", {}).get("fullTextUrl", []):
                        if url_item.get("documentStyle") == "pdf" and url_item.get("url"):
                            return url_item["url"], "Europe PMC"
        except Exception as e:
            logger.warning("Europe PMC resolution failed for %s: %s", clean_doi, e)

        return None, None

    finally:
        if should_close:
            await client.aclose()
