# academic-paper-mcp (Part of DPM Research)

[![Repository](https://img.shields.io/badge/GitHub-rico192%2Facademic--paper--mcp-blue?logo=github)](https://github.com/rico192/academic-paper-mcp)
[![Part of DPM Research](https://img.shields.io/badge/Part%20of-DPM%20Research-green)](https://github.com/rico192/academic-paper-mcp)

An open, high-performance **Model Context Protocol (MCP)** server that empowers AI Agents (**Antigravity**, **Claude Code**, **Claude Desktop**, **Cursor**, **Windsurf**, **Zed**, etc.) to search, fetch, rank, cite, and download academic papers across major scholarly databases:

- 🟢 **arXiv** (Free, no API key required)
- 🟢 **OpenAlex** (Free, 250M+ scholarly works, no API key required)
- 🟢 **Crossref** (Free, official DOI metadata repository, no API key required)
- 🟡 **Semantic Scholar** (AI2 graph search, free API key optional/recommended)
- 🔵 **Scopus (Elsevier)** (Curated peer-reviewed index, requires API Key)

---

## ✨ Features

- 🔍 **Multi-Database Search**: Queries arXiv, OpenAlex, Crossref, Semantic Scholar, and Scopus (Elsevier) concurrently in real time.
- 🧹 **Automatic Deduplication**: Merges duplicate records by DOI, arXiv ID, or title similarity so your AI context isn't cluttered.
- 🎯 **Relevance & Recency Ranking**: Scores papers based on query term overlap (weighted on title and abstract), citation count (logarithmic), recency, and open access availability.
- 📝 **Auto BibTeX Generation**: Instantly produces valid, formatted BibTeX citations ready for LaTeX or Word documents.
- 📥 **Direct PDF Downloader**: Downloads open-access paper PDFs directly to your workspace for immediate agent reading and analysis.
- ⚡ **Zero Setup Required for Open Databases**: Searches across arXiv, OpenAlex, and Crossref work out-of-the-box immediately without needing any API keys; simply add `SCOPUS_API_KEY` and `SEMANTIC_SCHOLAR_API_KEY` to unlock Scopus and Semantic Scholar indexing.

---

## 🔑 Database Sources & API Key Requirements

| Source | Default Status Without Keys | API Key Required? | Environment Variable | Function & Benefits |
|---|---|---|---|---|
| 🟢 **arXiv** | ✅ Active | ❌ No | *None needed* | Free open-access archive for CS, Math, and Physics. |
| 🟢 **OpenAlex** | ✅ Active | ❌ No | *Optional:* `OPENALEX_EMAIL` | 250M+ scholarly records worldwide. |
| 🟢 **Crossref** | ✅ Active | ❌ No | *Optional:* `CROSSREF_EMAIL` | Official global DOI registry and metadata. |
| 🟡 **Semantic Scholar** | ⏸️ **Skipped if no key** | 🔑 **YES (Required)** | `SEMANTIC_SCHOLAR_API_KEY` | Unlocks AI-powered citation graphs, TLDR summaries, and full abstracts (prevents 429 rate limits). |
| 🔵 **Scopus (Elsevier)** | ⏸️ **Skipped if no key** | 🔑 **YES (Required)** | `SCOPUS_API_KEY` *(+ opt `SCOPUS_INST_TOKEN`)* | Unlocks premier curated peer-reviewed Q1-Q4 index. |

> ⚠️ **CRITICAL FOR AI AGENTS & USERS:** 
> - **Both Scopus AND Semantic Scholar are SKIPPED by default** unless their respective API keys are provided in the MCP `env` configuration!
> - To get the full power of all 5 academic databases, **always include both `SCOPUS_API_KEY` and `SEMANTIC_SCHOLAR_API_KEY`** in your MCP settings.

---

## 🛠️ Tools Exposed to AI Agents

| Tool | Description |
|---|---|
| `search_papers` | Concurrent multi-database search across all databases with deduplication, ranking, year filtering, and BibTeX generation. Flexible limits (e.g. 10, 30, 50+ papers). |
| `get_paper_details` | Retrieve deep metadata, complete abstract, links, and BibTeX for a specific paper by DOI or arXiv ID. |
| `get_bibtex` | Generate formatted BibTeX citation for a DOI, arXiv ID, or title. |
| `download_paper_pdf` | Download academic paper PDF by DOI, arXiv ID, or URL. Automatically resolves legal open-access PDFs across Unpaywall, OpenAlex, and Europe PMC. If strictly paywalled, provides institutional EZproxy UNS access link. |
| `list_sources` | Inspect available academic search engines and their configuration status. |

---

## 🚀 Quick Start & Installation

You can run this MCP server via `uvx` directly from Git, or locally with `python` / `uv`.

### 1. Claude Code CLI

Add the MCP server directly using `claude mcp add`:

```bash
# Option A: Run directly from GitHub repository via uvx (Recommended)
claude mcp add academic-paper-mcp -s user \
  -e SCOPUS_API_KEY=your_scopus_api_key \
  -e SEMANTIC_SCHOLAR_API_KEY=your_s2_api_key \
  -- uvx --from git+https://github.com/rico192/academic-paper-mcp academic-paper-mcp

# Option B: Run from local directory using uv
claude mcp add academic-paper-mcp -s user -- uv --directory /path/to/academic-paper-mcp run academic-paper-mcp

# Option C: Run with local Python environment
claude mcp add academic-paper-mcp -s user -- python -m academic_paper_mcp.server
```

---

### 2. Google Antigravity & Gemini CLI

In your workspace or global Antigravity settings (`mcp_servers.json` or Antigravity Settings UI):

```json
{
  "mcpServers": {
    "academic-paper-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/rico192/academic-paper-mcp", "academic-paper-mcp"],
      "env": {
        "SCOPUS_API_KEY": "",
        "SEMANTIC_SCHOLAR_API_KEY": ""
      }
    }
  }
}
```

Or for a local checkout:

```json
{
  "mcpServers": {
    "academic-paper-mcp": {
      "command": "python",
      "args": ["-m", "academic_paper_mcp.server"],
      "cwd": "C:/path/to/academic-paper-mcp",
      "env": {
        "PYTHONPATH": "src"
      }
    }
  }
}
```

---

### 3. Claude Desktop

Edit your Claude Desktop configuration file:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "academic-paper-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/rico192/academic-paper-mcp", "academic-paper-mcp"],
      "env": {
        "SCOPUS_API_KEY": "",
        "SEMANTIC_SCHOLAR_API_KEY": ""
      }
    }
  }
}
```

---

### 4. Cursor / Windsurf / Zed

In your MCP configuration file (e.g. `.cursor/mcp.json` or Zed settings):

```json
{
  "mcpServers": {
    "academic-paper-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/academic-paper-mcp", "run", "academic-paper-mcp"],
      "env": {
        "SCOPUS_API_KEY": "",
        "SEMANTIC_SCHOLAR_API_KEY": ""
      }
    }
  }
}
```

---

## ⚙️ Environment Variables Reference

Create a `.env` file in the project folder or configure environment variables in your MCP client:

```ini
# Elsevier Scopus API Key (Get free key at: https://dev.elsevier.com)
SCOPUS_API_KEY=
# Optional: Elsevier Institutional Token for off-campus/remote access
SCOPUS_INST_TOKEN=

# Semantic Scholar API Key (Free key at: https://www.semanticscholar.org/product/api)
SEMANTIC_SCHOLAR_API_KEY=

# Polite pool identification for OpenAlex & Crossref (Recommended for faster response times)
OPENALEX_EMAIL=your-email@example.com
CROSSREF_EMAIL=your-email@example.com
```

*Note: If no API keys are provided, arXiv, OpenAlex, and Crossref will continue to work normally with 100% free public access. Provide `SCOPUS_API_KEY` and `SEMANTIC_SCHOLAR_API_KEY` to activate Scopus and Semantic Scholar.*

---

## 💻 Local Development & Testing

```bash
# Clone the repository
git clone https://github.com/rico192/academic-paper-mcp.git
cd academic-paper-mcp

# Install dependencies with uv or pip
pip install -e .

# Run test query
python -m academic_paper_mcp.server
```

---

## 📄 License

MIT License. Feel free to use, modify, and distribute.
