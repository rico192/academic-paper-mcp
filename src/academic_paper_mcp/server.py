from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
import re
import sys
from typing import Any, List, Optional

from dotenv import load_dotenv

# Ensure .env is loaded from current working directory or package root
load_dotenv()
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# Crucial: Configure logging strictly to sys.stderr to avoid corrupting stdio JSON-RPC
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
)
logger = logging.getLogger("academic_paper_mcp")

# Import MCP Server (compatible with both MCP 2.x and 1.x)
try:
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer(
        name="academic-paper-mcp",
        version="0.1.0",
        description="Academic literature search and citation MCP server for AI Agents",
    )
except (ImportError, ModuleNotFoundError):
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("academic-paper-mcp")

import httpx

from academic_paper_mcp.adapters import ADAPTER_REGISTRY, BaseAdapter
from academic_paper_mcp.citation import generate_bibtex
from academic_paper_mcp.deduplication import deduplicate_papers, normalize_arxiv_id, normalize_doi
from academic_paper_mcp.models import Paper
from academic_paper_mcp.ranking import rank_papers


def get_adapters() -> dict[str, BaseAdapter]:
    return {name: cls() for name, cls in ADAPTER_REGISTRY.items()}


@mcp.tool()
async def list_sources() -> str:
    """List all supported academic sources and their configuration status (arXiv, OpenAlex, Crossref, Semantic Scholar, Scopus). Shows which sources are active and which need an API key."""
    adapters = get_adapters()
    sources = []
    for name, adapter in adapters.items():
        sources.append({
            "name": adapter.name,
            "display_name": adapter.display_name,
            "configured": adapter.is_configured(),
            "requires_key": adapter.requires_key,
            "env_key": "SCOPUS_API_KEY" if adapter.name == "scopus" else ("SEMANTIC_SCHOLAR_API_KEY" if adapter.name == "semantic_scholar" else None),
            "description": adapter.description,
        })
    return json.dumps(sources, indent=2)


@mcp.tool()
async def search_papers(
    query: str,
    sources: Optional[List[str]] = None,
    limit_per_source: int = 10,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
) -> str:
    """Search academic papers across multiple databases (arXiv, OpenAlex, Crossref, Semantic Scholar, Scopus).
    
    Returns deduplicated, relevance-ranked papers with verified metadata (title, authors, year, venue, DOI, abstract, citations, open-access link, and BibTeX citation).
    
    API Key Notes:
    - arXiv, OpenAlex, Crossref: 100% active out-of-the-box (no API key needed).
    - Scopus: requires 'SCOPUS_API_KEY' in env. If not configured, Scopus is skipped.
    - Semantic Scholar: requires 'SEMANTIC_SCHOLAR_API_KEY' in env. If not configured, Semantic Scholar is skipped.
    
    Args:
        query: Academic topic or keywords (e.g. 'deep reinforcement learning robotics', 'electro-hydrostatic actuator PID').
        sources: Optional list of sources to search. Options: ['arxiv', 'openalex', 'crossref', 'semantic_scholar', 'scopus']. Default: all configured sources.
        limit_per_source: Number of papers to fetch per database (default 10, no artificial limit).
        year_min: Filter papers published in or after this year (e.g. 2021).
        year_max: Filter papers published in or before this year.
    """
    if not query or not query.strip():
        return json.dumps({"error": "Search query cannot be empty"})

    adapters = get_adapters()
    target_names = sources if sources else list(adapters.keys())

    adapters_to_query: list[BaseAdapter] = []
    active_sources: list[str] = []
    skipped_sources: list[str] = []

    for name in target_names:
        adapter = adapters.get(name.lower().strip())
        if not adapter:
            continue
        if adapter.is_configured():
            active_sources.append(adapter.name)
            adapters_to_query.append(adapter)
        else:
            skipped_sources.append(adapter.name)

    logger.info("Executing search for query: '%s' across sources: %s (limit: %d)", query, active_sources, limit_per_source)

    limit = max(1, limit_per_source)

    async def fetch_source(ad: BaseAdapter, client: httpx.AsyncClient) -> list[Paper]:
        try:
            return await ad.search(query, limit=limit, client=client)
        except Exception as e:
            logger.warning("Error fetching from %s: %s", ad.name, e)
            return []

    raw_papers: list[Paper] = []
    async with httpx.AsyncClient(timeout=20.0) as client:
        tasks = [fetch_source(ad, client) for ad in adapters_to_query]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                raw_papers.extend(res)

    # Filter by year if specified
    filtered = raw_papers
    if year_min is not None or year_max is not None:
        filtered = [
            p for p in filtered
            if (year_min is None or (p.year and p.year >= year_min))
            and (year_max is None or (p.year and p.year <= year_max))
        ]

    # Deduplicate and rank
    deduped = deduplicate_papers(filtered)
    ranked = rank_papers(deduped, query)

    output = []
    for p in ranked:
        output.append({
            "paper_id": p.paper_id,
            "source": p.source,
            "title": p.title,
            "authors": p.authors,
            "year": p.year,
            "venue": p.venue,
            "doi": p.doi,
            "arxiv_id": p.arxiv_id,
            "citation_count": p.citation_count,
            "url": p.url,
            "pdf_url": p.pdf_url,
            "abstract": p.abstract[:600] + "..." if p.abstract and len(p.abstract) > 600 else p.abstract,
            "is_open_access": p.is_open_access,
            "bibtex": p.bibtex,
        })

    response = {
        "query": query,
        "total_results": len(output),
        "active_sources": active_sources,
        "skipped_sources": skipped_sources,
        "papers": output,
    }
    return json.dumps(response, indent=2)


@mcp.tool()
async def get_paper_details(identifier: str) -> str:
    """Retrieve detailed metadata, abstract, open-access PDF link, and BibTeX citation for a specific paper.
    
    Args:
        identifier: DOI (e.g. '10.1145/3318464.3389700'), arXiv ID (e.g. '1706.03762' or 'arxiv:1706.03762'), or paper title.
    """
    clean_id = identifier.strip()
    norm_doi = normalize_doi(clean_id)
    norm_arxiv = normalize_arxiv_id(clean_id)

    adapters = get_adapters()
    candidate_papers: list[Paper] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        # If arXiv ID
        if norm_arxiv and re.match(r"^\d{4}\.\d{4,5}$", norm_arxiv):
            arxiv_adapter = adapters.get("arxiv")
            if arxiv_adapter:
                res = await arxiv_adapter.search(norm_arxiv, limit=1, client=client)
                candidate_papers.extend(res)

        # If DOI
        if norm_doi and "/" in norm_doi:
            crossref_adapter = adapters.get("crossref")
            if crossref_adapter:
                res = await crossref_adapter.search(norm_doi, limit=1, client=client)
                candidate_papers.extend(res)

            openalex_adapter = adapters.get("openalex")
            if openalex_adapter and not candidate_papers:
                res = await openalex_adapter.search(norm_doi, limit=1, client=client)
                candidate_papers.extend(res)

        # Fallback to general search if still empty
        if not candidate_papers:
            for ad in [adapters.get("openalex"), adapters.get("crossref"), adapters.get("arxiv")]:
                if ad and ad.is_configured():
                    res = await ad.search(clean_id, limit=1, client=client)
                    if res:
                        candidate_papers.extend(res)
                        break

    if not candidate_papers:
        return json.dumps({"error": f"No paper found matching identifier '{identifier}'"})

    paper = candidate_papers[0]
    return json.dumps(paper.model_dump(), indent=2)


@mcp.tool()
async def get_bibtex(identifier: str) -> str:
    """Generate a clean and valid BibTeX citation entry for a paper by DOI, arXiv ID, or title.
    
    Args:
        identifier: DOI (e.g. '10.1038/nature14539'), arXiv ID (e.g. '1706.03762'), or title.
    """
    details_str = await get_paper_details(identifier)
    details = json.loads(details_str)
    if "error" in details:
        return details["error"]

    bibtex = details.get("bibtex")
    if not bibtex:
        paper = Paper(**details)
        bibtex = generate_bibtex(paper)
    return bibtex


@mcp.tool()
async def download_paper_pdf(
    pdf_url_or_arxiv_id: str,
    save_directory: str = "./downloads",
    custom_filename: Optional[str] = None,
) -> str:
    """Download an open-access academic paper PDF to a local directory for reading/inspection.
    
    Args:
        pdf_url_or_arxiv_id: Direct PDF URL or arXiv ID (e.g. '1706.03762' or 'https://arxiv.org/pdf/1706.03762.pdf').
        save_directory: Local directory where the PDF should be saved (default: './downloads').
        custom_filename: Optional custom file name (e.g. 'attention_is_all_you_need.pdf').
    """
    target = pdf_url_or_arxiv_id.strip()

    # If arXiv ID is provided
    norm_arxiv = normalize_arxiv_id(target)
    if norm_arxiv and re.match(r"^\d{4}\.\d{4,5}$", norm_arxiv):
        target_url = f"https://arxiv.org/pdf/{norm_arxiv}.pdf"
        default_name = f"arxiv_{norm_arxiv}.pdf"
    elif target.startswith("http://") or target.startswith("https://"):
        target_url = target
        default_name = target.split("/")[-1].split("?")[0]
        if not default_name.endswith(".pdf"):
            default_name = f"paper_{abs(hash(target)) % 100000}.pdf"
    else:
        return json.dumps({"error": f"Invalid URL or arXiv ID: '{pdf_url_or_arxiv_id}'"})

    filename = custom_filename.strip() if custom_filename else default_name
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    save_path_dir = Path(save_directory).resolve()
    save_path_dir.mkdir(parents=True, exist_ok=True)
    destination_file = save_path_dir / filename

    logger.info("Downloading PDF from %s to %s", target_url, destination_file)

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        }
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            resp = await client.get(target_url, headers=headers)
            if resp.status_code != 200:
                return json.dumps({
                    "error": f"Failed to download PDF. Server responded with status code {resp.status_code}"
                })
            
            content_type = resp.headers.get("content-type", "").lower()
            if "html" in content_type and len(resp.content) < 5000:
                return json.dumps({
                    "error": "The URL returned an HTML webpage instead of a direct PDF document."
                })

            destination_file.write_bytes(resp.content)
            file_size_kb = round(len(resp.content) / 1024, 2)

            return json.dumps({
                "status": "success",
                "message": f"Successfully downloaded PDF ({file_size_kb} KB)",
                "saved_path": str(destination_file),
                "file_name": filename,
                "file_size_kb": file_size_kb,
            }, indent=2)

    except Exception as e:
        logger.error("Download failed: %s", e)
        return json.dumps({"error": f"PDF download failed: {str(e)}"})


def main():
    """Main stdio entrypoint for the MCP server."""
    logger.info("Starting academic-paper-mcp server on stdio...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
