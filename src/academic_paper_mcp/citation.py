from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from academic_paper_mcp.models import Paper


def generate_bibtex(paper: Paper) -> str:
    """Generate a clean and standard BibTeX citation string for a paper."""
    # Determine citation key: e.g. Vaswani2017Attention
    first_author = "Unknown"
    if paper.authors:
        # Extract last name from first author
        first_author_clean = paper.authors[0].strip()
        parts = first_author_clean.split()
        if parts:
            first_author = parts[-1]
    
    first_author = re.sub(r"[^\w]", "", first_author).capitalize() or "Author"
    year_str = str(paper.year) if paper.year else "nodate"

    # Extract meaningful first word of title
    first_word = ""
    if paper.title:
        words = re.findall(r"[A-Za-z0-9]+", paper.title)
        skip_words = {"a", "an", "the", "on", "in", "for", "of", "to", "and", "with", "by"}
        for w in words:
            if w.lower() not in skip_words:
                first_word = w.capitalize()
                break
        if not first_word and words:
            first_word = words[0].capitalize()
    if not first_word:
        first_word = "Paper"

    cite_key = f"{first_author}{year_str}{first_word}"

    # Determine entry type (article vs inproceedings)
    entry_type = "article"
    fields: list[str] = [
        f"  title = {{{paper.title}}}",
        f"  author = {{{' and '.join(paper.authors) if paper.authors else 'Unknown'}}}",
    ]

    if paper.year:
        fields.append(f"  year = {{{paper.year}}}")
    if paper.venue:
        fields.append(f"  journal = {{{paper.venue}}}")
    if paper.doi:
        fields.append(f"  doi = {{{paper.doi}}}")
    if paper.arxiv_id:
        fields.append(f"  eprint = {{{paper.arxiv_id}}}")
        fields.append(f"  archivePrefix = {{arXiv}}")
    if paper.url:
        fields.append(f"  url = {{{paper.url}}}")

    return f"@{entry_type}{{{cite_key},\n" + ",\n".join(fields) + "\n}"
