from __future__ import annotations

import os
from typing import Optional
import httpx

from academic_paper_mcp.adapters.base import BaseAdapter
from academic_paper_mcp.citation import generate_bibtex
from academic_paper_mcp.models import Paper


class SemanticScholarAdapter(BaseAdapter):
    name = "semantic_scholar"
    display_name = "Semantic Scholar"
    requires_key = True
    description = "AI2 Semantic Scholar academic graph search (free API key recommended)"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    def is_configured(self) -> bool:
        # We allow querying if configured, or can attempt public if key is absent
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        limit: int = 10,
        client: Optional[httpx.AsyncClient] = None,
    ) -> list[Paper]:
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": "paperId,title,abstract,authors,year,venue,externalIds,citationCount,isOpenAccess,url,openAccessPdf",
        }
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        try:
            if client is None:
                async with httpx.AsyncClient(timeout=15.0) as session:
                    resp = await session.get(
                        "https://api.semanticscholar.org/graph/v1/paper/search",
                        params=params,
                        headers=headers,
                    )
            else:
                resp = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params=params,
                    headers=headers,
                    timeout=15.0,
                )

            if resp.status_code != 200:
                # E.g. 429 rate limit or 403
                return []
            data = resp.json()
        except Exception:
            return []

        papers: list[Paper] = []
        for item in data.get("data") or []:
            paper_id = item.get("paperId")
            if not paper_id:
                continue

            authors = [
                a.get("name")
                for a in item.get("authors") or []
                if isinstance(a, dict) and a.get("name")
            ]
            ext_ids = item.get("externalIds") or {}
            open_access_pdf = item.get("openAccessPdf") or {}

            paper = Paper(
                paper_id=f"semantic_scholar:{paper_id}",
                source="semantic_scholar",
                title=item.get("title") or "Untitled",
                authors=authors,
                year=item.get("year"),
                venue=item.get("venue") or None,
                doi=ext_ids.get("DOI"),
                arxiv_id=ext_ids.get("ArXiv"),
                url=item.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}",
                pdf_url=open_access_pdf.get("url"),
                abstract=item.get("abstract"),
                citation_count=item.get("citationCount"),
                is_open_access=item.get("isOpenAccess"),
            )
            paper.bibtex = generate_bibtex(paper)
            papers.append(paper)

        return papers
