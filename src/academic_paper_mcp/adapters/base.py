from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
import httpx
from academic_paper_mcp.models import Paper


class BaseAdapter(ABC):
    name: str
    display_name: str
    requires_key: bool
    description: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if this adapter is configured and ready to query."""
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
        client: Optional[httpx.AsyncClient] = None,
    ) -> list[Paper]:
        """Execute paper search against the source API and return normalized Paper models."""
        ...
