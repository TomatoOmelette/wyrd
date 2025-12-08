# Wyrd

Personal book knowledge system with semantic search, knowledge graphs, and MCP integration.

*The web of knowledge, interconnected like fate itself.*

## Features

- **Semantic Search** - Query your book collection using natural language
- **Knowledge Graph** - Map concept relationships across sources
- **MCP Server** - Integrate with Claude and other LLM clients
- **Topic Extraction** - Automatically identify and organize topics
- **Human Curation** - YAML-based workflow for curating key insights
- **Multiple Backends** - ChromaDB (default), with pgvector/Neo4j options

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

### Using uv (recommended)

```bash
git clone https://github.com/yourusername/wyrd.git
cd wyrd
uv sync
source .venv/bin/activate
```

### Using pip

```bash
git clone https://github.com/yourusername/wyrd.git
cd wyrd
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Using Docker

```bash
docker build -t wyrd:latest .
docker-compose up
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
wyrd serve \
  --transport stdio  # or http
  --host 0.0.0.0 \
  --port 8000
```

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
| `WYRD_EMBEDDING_PROVIDER` | `local` | `local`, `openai`, or `voyage` |
| `WYRD_STORAGE_PATH` | `./storage` | Persistent storage directory |
| `WYRD_KNOWLEDGE_PATH` | `./knowledge` | User content directory |
| `WYRD_SYNTHESIS_PROVIDER` | `none` | `none`, `ollama`, `openai`, `anthropic` |

## Project Structure

```
wyrd/
├── src/wyrd/
│   ├── cli.py              # Command-line interface
│   ├── mcp_server/         # MCP server implementation
│   └── core/
│       ├── ingestion/      # Book parsing & chunking
│       ├── indexing/       # Storage backends
│       ├── retrieval/      # Search functionality
│       ├── synthesis/      # Response synthesis
│       └── topics/         # Topic management
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

MIT
