from __future__ import annotations

import re
from typing import Sequence
from academic_paper_mcp.models import Paper

NON_ALPHANUM_RE = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_title(title: str) -> str:
    """Normalize a title by lowercasing, stripping punctuation, and collapsing whitespace."""
    if not title:
        return ""
    text = NON_ALPHANUM_RE.sub(" ", title.lower())
    return " ".join(text.split())


def normalize_doi(doi: str | None) -> str | None:
    """Normalize DOI by stripping URLs and lowercase."""
    if not doi:
        return None
    d = doi.strip().lower()
    d = d.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "")
    return d.strip() or None


def normalize_arxiv_id(arxiv_id: str | None) -> str | None:
    """Normalize arXiv ID by removing version suffix (e.g. 1706.03762v7 -> 1706.03762)."""
    if not arxiv_id:
        return None
    a = arxiv_id.strip().lower()
    a = a.replace("arxiv:", "")
    a = a.split("v")[0]
    return a.strip() or None


def merge_two_papers(primary: Paper, secondary: Paper) -> Paper:
    """Merge metadata from secondary paper into primary paper, preferring richest fields."""
    merged_authors = primary.authors if len(primary.authors) >= len(secondary.authors) else secondary.authors
    merged_abstract = primary.abstract or secondary.abstract
    if primary.abstract and secondary.abstract:
        merged_abstract = primary.abstract if len(primary.abstract) >= len(secondary.abstract) else secondary.abstract

    merged_pdf_url = primary.pdf_url or secondary.pdf_url
    merged_url = primary.url or secondary.url

    cit1 = primary.citation_count or 0
    cit2 = secondary.citation_count or 0
    merged_citations = max(cit1, cit2) if (primary.citation_count is not None or secondary.citation_count is not None) else None

    return Paper(
        paper_id=primary.paper_id,
        source=f"{primary.source}+{secondary.source}" if primary.source != secondary.source else primary.source,
        title=primary.title,
        authors=merged_authors,
        year=primary.year or secondary.year,
        venue=primary.venue or secondary.venue,
        doi=primary.doi or secondary.doi,
        arxiv_id=primary.arxiv_id or secondary.arxiv_id,
        url=merged_url,
        pdf_url=merged_pdf_url,
        abstract=merged_abstract,
        citation_count=merged_citations,
        is_open_access=primary.is_open_access or secondary.is_open_access,
        bibtex=primary.bibtex or secondary.bibtex,
    )


def deduplicate_papers(papers: Sequence[Paper]) -> list[Paper]:
    """Deduplicate papers using DOI, arXiv ID, and normalized title matching."""
    doi_map: dict[str, int] = {}
    arxiv_map: dict[str, int] = {}
    title_map: dict[str, int] = {}

    unique_papers: list[Paper] = []

    for paper in papers:
        norm_doi = normalize_doi(paper.doi)
        norm_arxiv = normalize_arxiv_id(paper.arxiv_id)
        norm_title = normalize_title(paper.title)

        existing_idx: int | None = None

        if norm_doi and norm_doi in doi_map:
            existing_idx = doi_map[norm_doi]
        elif norm_arxiv and norm_arxiv in arxiv_map:
            existing_idx = arxiv_map[norm_arxiv]
        elif norm_title and len(norm_title) > 15 and norm_title in title_map:
            existing_idx = title_map[norm_title]

        if existing_idx is not None:
            unique_papers[existing_idx] = merge_two_papers(unique_papers[existing_idx], paper)
            if norm_doi:
                doi_map[norm_doi] = existing_idx
            if norm_arxiv:
                arxiv_map[norm_arxiv] = existing_idx
            if norm_title:
                title_map[norm_title] = existing_idx
        else:
            new_idx = len(unique_papers)
            unique_papers.append(paper)
            if norm_doi:
                doi_map[norm_doi] = new_idx
            if norm_arxiv:
                arxiv_map[norm_arxiv] = new_idx
            if norm_title:
                title_map[norm_title] = new_idx

    return unique_papers
