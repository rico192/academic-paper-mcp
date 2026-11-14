from __future__ import annotations

import os
import re
from typing import Optional
import httpx

from academic_paper_mcp.adapters.base import BaseAdapter
from academic_paper_mcp.citation import generate_bibtex
from academic_paper_mcp.models import Paper

TAG_RE = re.compile(r"<[^>]+>")


def strip_html_tags(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = TAG_RE.sub(" ", text)
    return " ".join(cleaned.split()).strip() or None


class CrossrefAdapter(BaseAdapter):
    name = "crossref"
    display_name = "Crossref"
    requires_key = False
    description = "Official digital object identifier (DOI) registration agency metadata repository"

    def __init__(self, email: Optional[str] = None) -> None:
        self.email = email or os.getenv("CROSSREF_EMAIL")

    def is_configured(self) -> bool:
        return True

    async def search(
        self,
        query: str,
        limit: int = 10,
        client: Optional[httpx.AsyncClient] = None,
    ) -> list[Paper]:
        params: dict[str, str | int] = {
            "query": query,
            "rows": min(limit, 1000),
        }
        if self.email:
            params["mailto"] = self.email

        headers = {
            "User-Agent": f"AcademicPaperMCP/0.1.0 (mailto:{self.email or 'dev@mcp.org'})"
        }

        try:
            if client is None:
                async with httpx.AsyncClient(timeout=15.0) as session:
                    resp = await session.get("https://api.crossref.org/works", params=params, headers=headers)
            else:
                resp = await client.get("https://api.crossref.org/works", params=params, headers=headers, timeout=15.0)

            if resp.status_code != 200:
                return []
            data = resp.json()
        except Exception:
            return []

        message = data.get("message") or {}
        items = message.get("items") or []

        papers: list[Paper] = []
        for item in items:
            doi = item.get("DOI")
            if not doi:
                continue

            raw_titles = item.get("title") or []
            title = raw_titles[0] if raw_titles else "Untitled"

            authors: list[str] = []
            for a in item.get("author") or []:
                if isinstance(a, dict):
                    given = a.get("given", "").strip()
                    family = a.get("family", "").strip()
                    name = f"{given} {family}".strip() if given or family else a.get("name", "").strip()
                    if name:
                        authors.append(name)

            year = None
            published_print = item.get("published-print") or item.get("published-online") or item.get("created") or {}
            date_parts = published_print.get("date-parts")
            if date_parts and isinstance(date_parts, list) and len(date_parts) > 0 and len(date_parts[0]) > 0:
                try:
                    year = int(date_parts[0][0])
                except (ValueError, TypeError):
                    pass

            container_titles = item.get("container-title") or []
            venue = container_titles[0] if container_titles else None

            pdf_url = None
            for link in item.get("link") or []:
                if isinstance(link, dict) and link.get("content-type") == "application/pdf":
                    pdf_url = link.get("URL")
                    break

            raw_abstract = item.get("abstract")
            abstract = strip_html_tags(raw_abstract)

            is_oa = None
            for license_item in item.get("license") or []:
                if isinstance(license_item, dict) and license_item.get("URL"):
                    is_oa = True
                    break

            paper = Paper(
                paper_id=f"crossref:{doi}",
                source="crossref",
                title=title,
                authors=authors,
                year=year,
                venue=venue,
                doi=doi,
                arxiv_id=None,
                url=item.get("URL") or f"https://doi.org/{doi}",
                pdf_url=pdf_url,
                abstract=abstract,
                citation_count=item.get("is-referenced-by-count"),
                is_open_access=is_oa,
            )
            paper.bibtex = generate_bibtex(paper)
            papers.append(paper)

        return papers
