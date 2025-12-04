# Wyrd

> *The web of knowledge, interconnected like fate itself.*

Wyrd is a personal book knowledge system that transforms your ebook library into a searchable, interconnected knowledge base. It combines semantic search, knowledge graphs, and the Model Context Protocol (MCP) to let AI assistants like Claude draw on your personal library when providing advice.

## Features

- **Semantic Search**: Find relevant passages by meaning, not just keywords
- **Knowledge Graph**: Connect concepts across books to see how ideas relate
- **Human Curation**: Optionally enhance automatic indexing with curated digests
- **MCP Integration**: Works with Claude Desktop and other MCP-compatible AI assistants
- **Source Traceability**: Every piece of advice traces back to book, chapter, and location
- **Context Efficient**: Applies Anthropic's MCP optimization patterns to minimize token usage

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/username/wyrd.git
cd wyrd

# Create your knowledge directory
mkdir -p knowledge/sources

# Start Wyrd
docker compose up -d

# Add a book
docker compose exec wyrd wyrd add /app/knowledge/sources/my-book.epub --slug my-book
```

### Using uv (For Development)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/username/wyrd.git
cd wyrd
uv sync

# Add a book
uv run wyrd add ~/Books/my-book.epub --slug my-book

# Start the MCP server
uv run wyrd serve
```

## Claude Desktop Integration

Add Wyrd to your Claude Desktop configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux**: `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "wyrd": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "${HOME}/wyrd-knowledge:/app/knowledge:ro",
        "-v", "wyrd-storage:/app/storage",
        "ghcr.io/username/wyrd:latest"
      ]
    }
  }
}
```

Or if running natively with uv:

```json
{
  "mcpServers": {
    "wyrd": {
      "command": "uv",
      "args": ["--directory", "/path/to/wyrd", "run", "wyrd", "serve"]
    }
  }
}
```

## CLI Commands

```bash
# Book management
wyrd add <file> --slug <slug>     # Add a book
wyrd remove <slug>                 # Remove a book
wyrd list                          # List all books

# Indexing
wyrd build                         # Rebuild all indexes
wyrd build --source <slug>         # Rebuild one source

# Server
wyrd serve                         # Start MCP server (stdio)
wyrd serve --transport http        # Start HTTP API

# Utilities
wyrd search "query"                # Test search
wyrd topics                        # List topics
wyrd concepts                      # List concepts
```

## MCP Tools

Wyrd exposes these tools to AI assistants:

| Tool | Description |
|------|-------------|
| `explore_library` | Navigate the knowledge structure progressively |
| `search_knowledge` | Semantic search with configurable detail levels |
| `get_advice` | RAG with server-side synthesis |
| `compare_sources` | Compare how different books approach a topic |
| `trace_concept` | Traverse concept relationships in the knowledge graph |

## Architecture

Wyrd applies [Anthropic's MCP context optimization patterns](https://www.anthropic.com/engineering/code-execution-with-mcp):

- **Progressive Discovery**: AI explores the library on-demand, not all at once
- **Configurable Detail**: Request minimal info first, drill down as needed
- **Server-Side Synthesis**: Process and summarize before returning to the AI
- **Knowledge Graph**: Connect concepts across sources for richer context

## Directory Structure

```
wyrd/
├── knowledge/           # Your content (gitignored in your instance)
│   ├── sources/         # Book metadata and optional curation
│   │   └── {slug}/
│   │       ├── metadata.yaml
│   │       ├── philosophy.yaml   # Optional
│   │       ├── principles.yaml   # Optional
│   │       └── strategies.yaml   # Optional
│   ├── topics/
│   │   └── registry.yaml
│   └── concepts/
│       └── relationships.yaml
│
├── storage/             # Generated indexes (gitignored)
│   ├── vectors/         # ChromaDB
│   ├── graph/           # NetworkX
│   └── metadata.db      # SQLite
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `WYRD_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `WYRD_STORAGE_PATH` | `./storage` | Path to index storage |
| `WYRD_KNOWLEDGE_PATH` | `./knowledge` | Path to knowledge content |
| `WYRD_SYNTHESIS_PROVIDER` | `none` | Synthesis LLM: none, ollama, openai, anthropic |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Etymology

In Old English, *wyrd* (pronounced "weird") refers to fate or personal destiny—the interconnected web of events that shapes one's life. We chose this name because Wyrd weaves together knowledge from many sources into an interconnected web, much like the threads of fate.
