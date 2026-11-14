from __future__ import annotations

import os
from typing import Optional
import httpx

from academic_paper_mcp.adapters.base import BaseAdapter
from academic_paper_mcp.citation import generate_bibtex
from academic_paper_mcp.models import Paper


class ScopusAdapter(BaseAdapter):
    name = "scopus"
    display_name = "Scopus (Elsevier)"
    requires_key = True
    description = "Elsevier Scopus curated abstract and citation database"

    def __init__(
        self,
        api_key: Optional[str] = None,
        inst_token: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("SCOPUS_API_KEY") or os.getenv("ELSEVIER_API_KEY")
        self.inst_token = inst_token or os.getenv("SCOPUS_INST_TOKEN")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def search(
        self,
        query: str,
        limit: int = 10,
        client: Optional[httpx.AsyncClient] = None,
    ) -> list[Paper]:
        if not self.is_configured():
            return []

        scopus_query = f"TITLE-ABS-KEY({query})"
        # Scopus allows max 25 per request for basic keys, up to 100 for institutional tokens
        max_scopus_count = 100 if self.inst_token else 25
        params = {
            "query": scopus_query,
            "count": min(limit, max_scopus_count),
        }
        headers = {
            "X-ELS-APIKey": self.api_key or "",
            "Accept": "application/json",
        }
        if self.inst_token:
            headers["X-ELS-Insttoken"] = self.inst_token

        try:
            if client is None:
                async with httpx.AsyncClient(timeout=15.0) as session:
                    resp = await session.get("https://api.elsevier.com/content/search/scopus", params=params, headers=headers)
            else:
                resp = await client.get("https://api.elsevier.com/content/search/scopus", params=params, headers=headers, timeout=15.0)

            if resp.status_code != 200:
                return []
            data = resp.json()
        except Exception:
            return []

        search_results = data.get("search-results") or {}
        entries = search_results.get("entry") or []

        papers: list[Paper] = []
        for item in entries:
            if "error" in item:
                continue

            eid = item.get("eid")
            raw_id = item.get("dc:identifier") or ""
            scopus_id = raw_id.replace("SCOPUS_ID:", "") if "SCOPUS_ID:" in raw_id else raw_id
            native_id = eid or scopus_id
            if not native_id:
                continue

            title = item.get("dc:title") or "Untitled"
            authors = []
            creator = item.get("dc:creator")
            if creator:
                authors.append(creator)

            year = None
            cover_date = item.get("prism:coverDate") or ""
            if cover_date and len(cover_date) >= 4 and cover_date[:4].isdigit():
                try:
                    year = int(cover_date[:4])
                except ValueError:
                    pass

            venue = item.get("prism:publicationName")
            doi = item.get("prism:doi")

            cited_by_count = None
            raw_citations = item.get("citedby-count")
            if raw_citations is not None:
                try:
                    cited_by_count = int(raw_citations)
                except (ValueError, TypeError):
                    pass

            url = None
            for lk in item.get("link") or []:
                if isinstance(lk, dict) and lk.get("@ref") == "scopus":
                    url = lk.get("@href")
                    break
            if not url:
                url = item.get("prism:url")

            is_oa = item.get("openaccess") == "1" or item.get("openaccessFlag") is True

            paper = Paper(
                paper_id=f"scopus:{native_id}",
                source="scopus",
                title=title,
                authors=authors,
                year=year,
                venue=venue,
                doi=doi,
                arxiv_id=None,
                url=url,
                pdf_url=None,
                abstract=None,
                citation_count=cited_by_count,
                is_open_access=is_oa,
            )
            paper.bibtex = generate_bibtex(paper)
            papers.append(paper)

        return papers
