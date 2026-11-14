import asyncio
import pytest

from academic_paper_mcp.adapters.arxiv import ArxivAdapter
from academic_paper_mcp.citation import generate_bibtex
from academic_paper_mcp.deduplication import deduplicate_papers, normalize_doi, normalize_title
from academic_paper_mcp.models import Paper
from academic_paper_mcp.ranking import rank_papers
from academic_paper_mcp.server import list_sources, search_papers


def test_normalization():
    assert normalize_title("Deep Learning: A Comprehensive Survey!") == "deep learning a comprehensive survey"
    assert normalize_doi("https://doi.org/10.1145/3318464") == "10.1145/3318464"


def test_bibtex_generation():
    p = Paper(
        paper_id="arxiv:1706.03762",
        source="arxiv",
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
        year=2017,
        venue="NeurIPS",
        arxiv_id="1706.03762",
    )
    bib = generate_bibtex(p)
    assert "@article{Vaswani2017Attention" in bib
    assert "author = {Ashish Vaswani and Noam Shazeer and Niki Parmar}" in bib
    assert "year = {2017}" in bib


def test_deduplication():
    p1 = Paper(
        paper_id="arxiv:1706.03762",
        source="arxiv",
        title="Attention Is All You Need",
        authors=["Ashish Vaswani"],
        year=2017,
        arxiv_id="1706.03762",
    )
    p2 = Paper(
        paper_id="openalex:W12345",
        source="openalex",
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer"],
        year=2017,
        arxiv_id="1706.03762",
    )
    deduped = deduplicate_papers([p1, p2])
    assert len(deduped) == 1
    assert len(deduped[0].authors) == 2


@pytest.mark.asyncio
async def test_list_sources():
    sources_json = await list_sources()
    assert "arxiv" in sources_json
    assert "openalex" in sources_json
    assert "crossref" in sources_json
    assert "semantic_scholar" in sources_json
    assert "scopus" in sources_json
