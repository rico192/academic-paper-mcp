from __future__ import annotations

import os
from typing import Optional
import httpx

from academic_paper_mcp.adapters.base import BaseAdapter
from academic_paper_mcp.citation import generate_bibtex
from academic_paper_mcp.models import Paper


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    if not inverted_index or not isinstance(inverted_index, dict):
        return None
    pos_to_word: dict[int, str] = {}
    for word, positions in inverted_index.items():
        if isinstance(positions, list):
            for pos in positions:
                pos_to_word[pos] = word
    if not pos_to_word:
        return None
    max_pos = max(pos_to_word.keys())
    words = [pos_to_word.get(i, "") for i in range(max_pos + 1)]
    return " ".join(words).strip() or None


class OpenAlexAdapter(BaseAdapter):
    name = "openalex"
    display_name = "OpenAlex"
    requires_key = False
    description = "Open catalog of 250M+ scholarly works with full citation and open-access data"

    def __init__(self, email: Optional[str] = None) -> None:
        self.email = email or os.getenv("OPENALEX_EMAIL")

    def is_configured(self) -> bool:
        return True

    async def search(
        self,
        query: str,
        limit: int = 10,
        client: Optional[httpx.AsyncClient] = None,
    ) -> list[Paper]:
        params: dict[str, str | int] = {
            "search": query,
            "per-page": min(limit, 200),
        }
        if self.email:
            params["mailto"] = self.email

        headers = {
            "User-Agent": f"AcademicPaperMCP/0.1.0 (mailto:{self.email or 'dev@mcp.org'})"
        }

        try:
            if client is None:
                async with httpx.AsyncClient(timeout=15.0) as session:
                    resp = await session.get("https://api.openalex.org/works", params=params, headers=headers)
            else:
                resp = await client.get("https://api.openalex.org/works", params=params, headers=headers, timeout=15.0)

            if resp.status_code != 200:
                return []
            data = resp.json()
        except Exception:
            return []

        papers: list[Paper] = []
        for item in data.get("results") or []:
            raw_id = item.get("id") or ""
            openalex_id = raw_id.split("/")[-1] if "/" in raw_id else raw_id

            title = item.get("display_name") or item.get("title") or "Untitled"
            authors: list[str] = []
            for authorship in item.get("authorships") or []:
                author_obj = authorship.get("author") or {}
                name = author_obj.get("display_name")
                if name:
                    authors.append(name.strip())

            year = item.get("publication_year")

            venue = None
            primary_loc = item.get("primary_location") or {}
            source_obj = primary_loc.get("source") or {}
            if source_obj.get("display_name"):
                venue = source_obj.get("display_name")

            raw_doi = item.get("doi")
            doi = raw_doi.replace("https://doi.org/", "").replace("http://doi.org/", "") if raw_doi else None

            pdf_url = None
            open_access_info = item.get("open_access") or {}
            is_oa = open_access_info.get("is_oa", False)
            oa_url = open_access_info.get("oa_url")
            if oa_url and oa_url.endswith(".pdf"):
                pdf_url = oa_url
            elif primary_loc.get("pdf_url"):
                pdf_url = primary_loc.get("pdf_url")

            abstract = reconstruct_abstract(item.get("abstract_inverted_index"))

            paper = Paper(
                paper_id=f"openalex:{openalex_id}",
                source="openalex",
                title=title,
                authors=authors,
                year=year,
                venue=venue,
                doi=doi,
                arxiv_id=None,
                url=raw_doi or (f"https://openalex.org/{openalex_id}" if openalex_id else None),
                pdf_url=pdf_url,
                abstract=abstract,
                citation_count=item.get("cited_by_count"),
                is_open_access=is_oa,
            )
            paper.bibtex = generate_bibtex(paper)
            papers.append(paper)

        return papers
