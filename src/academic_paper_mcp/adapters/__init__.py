from __future__ import annotations

from typing import Dict, Type
from academic_paper_mcp.adapters.base import BaseAdapter
from academic_paper_mcp.adapters.arxiv import ArxivAdapter
from academic_paper_mcp.adapters.openalex import OpenAlexAdapter
from academic_paper_mcp.adapters.crossref import CrossrefAdapter
from academic_paper_mcp.adapters.semantic_scholar import SemanticScholarAdapter
from academic_paper_mcp.adapters.scopus import ScopusAdapter

ADAPTER_REGISTRY: Dict[str, Type[BaseAdapter]] = {
    "arxiv": ArxivAdapter,
    "openalex": OpenAlexAdapter,
    "crossref": CrossrefAdapter,
    "semantic_scholar": SemanticScholarAdapter,
    "scopus": ScopusAdapter,
}

__all__ = [
    "BaseAdapter",
    "ArxivAdapter",
    "OpenAlexAdapter",
    "CrossrefAdapter",
    "SemanticScholarAdapter",
    "ScopusAdapter",
    "ADAPTER_REGISTRY",
]
