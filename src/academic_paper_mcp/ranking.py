from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Sequence
from academic_paper_mcp.models import Paper

TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def compute_relevance_score(paper: Paper, query_tokens: set[str], current_year: int) -> float:
    if not query_tokens:
        return 0.0

    title_tokens = set(tokenize(paper.title))
    abstract_tokens = set(tokenize(paper.abstract or ""))

    # Title match gives higher weight
    title_overlap = len(query_tokens & title_tokens) / max(len(query_tokens), 1)
    abstract_overlap = len(query_tokens & abstract_tokens) / max(len(query_tokens), 1)

    keyword_score = (title_overlap * 4.0) + (abstract_overlap * 2.0)

    # Citation bonus (log scaled)
    cit_score = 0.0
    if paper.citation_count and paper.citation_count > 0:
        cit_score = min(math.log10(paper.citation_count + 1) * 0.5, 3.0)

    # Recency bonus
    recency_score = 0.0
    if paper.year and paper.year > 1900:
        age = max(0, current_year - paper.year)
        recency_score = max(0.0, 1.0 - (age * 0.05))

    # Open Access bonus
    oa_score = 0.5 if (paper.is_open_access or paper.pdf_url) else 0.0

    return keyword_score + cit_score + recency_score + oa_score


def rank_papers(papers: Sequence[Paper], query: str) -> list[Paper]:
    """Rank papers by multi-factor score: query overlap in title/abstract, citations, recency, and open access."""
    query_tokens = set(tokenize(query))
    current_year = datetime.now(timezone.utc).year

    scored = [
        (compute_relevance_score(p, query_tokens, current_year), p)
        for p in papers
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]
