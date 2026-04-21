# Wyrd

Personal RAG system for your book library. Semantic search with citations, optional LLM synthesis, and MCP integration for Claude.

Named after the Old English word for *fate* — a nod to how the books you read shape how you think.

## Features

- **Semantic search** — query your library in natural language, get passages back with book/chapter citations
- **MCP server** — four tools (`search_knowledge`, `explore_library`, `get_advice`, `compare_sources`) usable from Claude Desktop or any MCP client
- **Topic extraction** — surface recurring ideas across sources
- **Human curation** — optional YAML workflow for hand-curating principles and strategies from a book
- **Local by default** — runs with `sentence-transformers` and ChromaDB; synthesis falls back to a rule-based extractor when no LLM is configured

*Experimental:* a concept knowledge graph is wired up behind `wyrd concepts` (NetworkX-backed) but not yet integrated into search or the MCP tools.

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

### Using uv (recommended)

```bash
git clone https://github.com/TomatoOmelette/wyrd.git
cd wyrd
uv sync
source .venv/bin/activate
```

### Using pip

```bash
git clone https://github.com/TomatoOmelette/wyrd.git
cd wyrd
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Using Docker

```bash
docker build -t wyrd:latest .
docker compose up
```

## Quick Start

```bash
# Add a book
wyrd add ~/Books/my-book.epub --subject "topic-name"

# Search your library
wyrd search "your question here"

# Start MCP server for Claude integration
wyrd serve --transport stdio
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `wyrd add <file>` | Add a book to the knowledge base |
| `wyrd remove <slug>` | Remove a book |
| `wyrd list` | List all books |
| `wyrd search <query>` | Search the knowledge base |
| `wyrd chapters <slug>` | List chapters in a book |
| `wyrd summarize <slug> <chapter>` | Summarize a chapter using an LLM |
| `wyrd serve` | Start the MCP server |
| `wyrd build` | Build/rebuild indexes |
| `wyrd subjects` | List all subjects |
| `wyrd topics` | List/search topics |
| `wyrd concepts` | List/search concepts |

### Add Options

```bash
wyrd add book.epub \
  --slug custom-slug \
  --subject "parenting" \
  --title "Custom Title" \
  --author "Author Name" \
  --chunk-size 512 \
  --chunk-overlap 50 \
  --extract-topics \
  --yes  # Skip confirmation
```

### Search Options

```bash
wyrd search "emotion coaching" \
  --limit 10 \
  --source book-slug \
  --subject parenting
```

### Serve Options

```bash
# --transport: stdio (default) or http
wyrd serve \
  --transport stdio \
  --host 0.0.0.0 \
  --port 8000
```

### Summarize Options

```bash
# --provider: ollama, openai, or anthropic (model name is provider-specific)
wyrd summarize my-book 1 \
  --provider ollama \
  --model llama3.2
```

Summarization uses `WYRD_SYNTHESIS_PROVIDER` env var by default. Falls back to rule-based extraction if no LLM is configured.

### Curation Commands

```bash
wyrd curate init <slug>       # Generate YAML templates
wyrd curate validate <path>   # Validate curation files
wyrd curate import <path>     # Import curated content
```

## MCP Tools

The MCP server exposes four tools:

| Tool | Purpose |
|------|---------|
| `search_knowledge` | Semantic search with optional synthesis |
| `explore_library` | Browse subjects and books |
| `get_advice` | Get synthesized advice on a topic |
| `compare_sources` | Compare how sources approach a topic |

### Claude Desktop Configuration

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "wyrd": {
      "command": "wyrd",
      "args": ["serve", "--transport", "stdio"]
    }
  }
}
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `WYRD_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `WYRD_EMBEDDING_PROVIDER` | `local` | Only `local` is currently implemented (`openai`, `voyage` are placeholders) |
| `WYRD_STORAGE_PATH` | `./storage` | Persistent storage directory |
| `WYRD_KNOWLEDGE_PATH` | `./knowledge` | User content directory |
| `WYRD_SYNTHESIS_PROVIDER` | `none` | `none`, `ollama`, `openai`, `anthropic` |

## Project Structure

```
wyrd/
├── src/wyrd/
│   ├── cli/                # Command-line interface (typer)
│   ├── mcp_server/         # MCP server implementation
│   ├── curation/           # YAML curation models, validator, importer
│   └── core/
│       ├── ingestion/      # Book parsing & chunking
│       ├── indexing/       # Vector store, metadata (SQLite), knowledge graph
│       ├── retrieval/      # Semantic search
│       ├── synthesis/      # Rule-based + LLM synthesis
│       └── topics/         # Topic extraction & registry
├── knowledge/              # User content (books, topics, concepts)
├── storage/                # Generated indexes (gitignored)
└── tests/                  # Test suite
```

## Testing

```bash
pytest tests/
pytest tests/test_cli.py -v
```

## License

MIT — see [LICENSE](LICENSE).
