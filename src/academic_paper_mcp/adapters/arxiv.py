from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional
import httpx

from academic_paper_mcp.adapters.base import BaseAdapter
from academic_paper_mcp.citation import generate_bibtex
from academic_paper_mcp.models import Paper

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


class ArxivAdapter(BaseAdapter):
    name = "arxiv"
    display_name = "arXiv"
    requires_key = False
    description = "Open-access archive for physics, computer science, mathematics, and quantitative biology"

    def is_configured(self) -> bool:
        return True

    async def search(
        self,
        query: str,
        limit: int = 10,
        client: Optional[httpx.AsyncClient] = None,
    ) -> list[Paper]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        try:
            if client is None:
                async with httpx.AsyncClient(timeout=15.0) as session:
                    resp = await session.get("https://export.arxiv.org/api/query", params=params)
            else:
                resp = await client.get("https://export.arxiv.org/api/query", params=params, timeout=15.0)
            
            if resp.status_code != 200:
                return []
            xml_text = resp.text
            root = ET.fromstring(xml_text)
        except Exception:
            return []

        papers: list[Paper] = []

        for entry in root.findall(f"{ATOM_NS}entry"):
            id_el = entry.find(f"{ATOM_NS}id")
            raw_id = id_el.text.strip() if id_el is not None and id_el.text else ""
            if not raw_id:
                continue

            # e.g. http://arxiv.org/abs/1706.03762v7 -> 1706.03762
            arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id
            clean_arxiv_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id

            title_el = entry.find(f"{ATOM_NS}title")
            raw_title = title_el.text if title_el is not None and title_el.text else "Untitled"
            title = " ".join(raw_title.split())

            summary_el = entry.find(f"{ATOM_NS}summary")
            abstract = " ".join(summary_el.text.split()) if summary_el is not None and summary_el.text else None

            authors: list[str] = []
            for author_el in entry.findall(f"{ATOM_NS}author"):
                name_el = author_el.find(f"{ATOM_NS}name")
                if name_el is not None and name_el.text:
                    authors.append(name_el.text.strip())

            published_el = entry.find(f"{ATOM_NS}published")
            published_str = published_el.text.strip() if published_el is not None and published_el.text else ""
            year = None
            if published_str and len(published_str) >= 4 and published_str[:4].isdigit():
                year = int(published_str[:4])

            doi_el = entry.find(f"{ARXIV_NS}doi")
            doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None

            pdf_url = f"https://arxiv.org/pdf/{clean_arxiv_id}.pdf"
            paper_url = f"https://arxiv.org/abs/{clean_arxiv_id}"

            p = Paper(
                paper_id=f"arxiv:{clean_arxiv_id}",
                source="arxiv",
                title=title,
                authors=authors,
                year=year,
                venue="arXiv",
                doi=doi,
                arxiv_id=clean_arxiv_id,
                url=paper_url,
                pdf_url=pdf_url,
                abstract=abstract,
                citation_count=None,
                is_open_access=True,
            )
            p.bibtex = generate_bibtex(p)
            papers.append(p)

        return papers
