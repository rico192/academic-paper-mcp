from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class Paper(BaseModel):
    paper_id: str
    source: str
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    abstract: Optional[str] = None
    citation_count: Optional[int] = None
    is_open_access: Optional[bool] = None
    bibtex: Optional[str] = None


class SourceStatus(BaseModel):
    name: str
    display_name: str
    configured: bool
    requires_key: bool
    description: str
