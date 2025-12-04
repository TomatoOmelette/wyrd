# Wyrd: Architecture and Design

A portable, open-source system for building personal knowledge bases from books with semantic search, knowledge graphs, and MCP integration for LLM-powered retrieval.

## Project Goals

1. **No content included** - Ships empty; users add their own books
2. **Cross-platform** - Runs on macOS and Linux via Docker or native Python
3. **Context-efficient** - Applies Anthropic's MCP patterns to minimize token usage
4. **Hybrid retrieval** - Combines vector search, knowledge graphs, and human curation
5. **Source traceability** - Every piece of advice traces back to book/chapter/location

---

## Architecture Overview

```
wyrd/
├── src/wyrd/
│   ├── core/
│   │   ├── ingestion/           # ePub/PDF → chunks → embeddings
│   │   │   ├── epub.py          # ePub parser (ebooklib)
│   │   │   ├── pdf.py           # PDF parser (pymupdf)
│   │   │   ├── chunker.py       # Smart chunking with overlap
│   │   │   └── embedder.py      # Generate embeddings
│   │   │
│   │   ├── indexing/            # Storage backends
│   │   │   ├── vectors.py       # ChromaDB or pgvector
│   │   │   ├── graph.py         # NetworkX (small) or Neo4j (large)
│   │   │   └── metadata.py      # SQLite for book/chapter metadata
│   │   │
│   │   ├── retrieval/           # Search and traversal
│   │   │   ├── semantic.py      # Vector similarity search
│   │   │   ├── graph_query.py   # Concept relationship traversal
│   │   │   └── hybrid.py        # Combined retrieval strategies
│   │   │
│   │   └── synthesis/           # Pre-LLM processing (MCP pattern)
│   │       ├── summarizer.py    # Condense retrieved chunks
│   │       ├── deduplicator.py  # Remove redundant content
│   │       └── formatter.py     # Structure for LLM consumption
│   │
│   ├── mcp_server/              # MCP interface
│   │   ├── server.py            # Main MCP server (stdio transport)
│   │   ├── tools/
│   │   │   ├── explore.py       # Progressive library discovery
│   │   │   ├── search.py        # Semantic search with detail levels
│   │   │   ├── advise.py        # RAG + synthesis for questions
│   │   │   ├── compare.py       # Cross-source comparison
│   │   │   └── trace.py         # Knowledge graph traversal
│   │   └── resources/           # MCP resources (read-only data)
│   │
│   ├── curation/                # Human curation workflow
│   │   ├── models.py            # YAML data models
│   │   ├── importer.py          # Import curated YAML
│   │   └── validator.py         # Validate curation format
│   │
│   └── cli/                     # Command-line interface
│       ├── __init__.py          # Main CLI app (typer)
│       └── __main__.py          # Entry point
│
├── knowledge/                   # User's content (gitignored in template)
│   ├── sources/                 # Book metadata + curated digests
│   │   └── {slug}/
│   │       ├── metadata.yaml
│   │       ├── philosophy.yaml  # Optional curation
│   │       ├── principles.yaml  # Optional curation
│   │       └── strategies.yaml  # Optional curation
│   │
│   ├── topics/                  # Topic taxonomy
│   │   └── registry.yaml
│   │
│   └── concepts/                # Knowledge graph definitions
│       └── relationships.yaml
│
├── storage/                     # Generated indexes (gitignored)
│   ├── vectors/                 # ChromaDB persistent storage
│   ├── graph/                   # NetworkX pickle or Neo4j
│   └── metadata.db              # SQLite
│
├── tests/
├── docs/
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## MCP Context Optimization Patterns

Based on [Anthropic's code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp), we apply these patterns:

### 1. Progressive Tool Discovery

Instead of exposing all knowledge upfront, let the agent navigate:

```python
@mcp_tool
def explore_library(
    path: str = "/",
    detail: Literal["names", "summaries", "full"] = "names"
) -> ExploreResult:
    """
    Navigate the knowledge structure progressively.

    Paths:
      /                     → List sources and topics
      /sources              → List all books
      /sources/{slug}       → Book details
      /topics               → List all topics
      /topics/{topic}       → Topic details
      /concepts             → List concept clusters
      /concepts/{concept}   → Concept and relationships

    Detail levels:
      names     → Just identifiers (minimal tokens)
      summaries → One-line descriptions
      full      → Complete information
    """
```

**Token savings**: Agent requests `/topics` with `detail="names"` first, then drills into specific topics only as needed.

### 2. Search with Configurable Detail

```python
@mcp_tool
def search_knowledge(
    query: str,
    scope: list[str] | None = None,    # ["source:good-inside", "topic:tantrums"]
    detail: Literal["citations", "summaries", "passages"] = "summaries",
    limit: int = 5
) -> list[SearchResult]:
    """
    Semantic search with server-side synthesis.

    Detail levels:
      citations  → Source references only (book, chapter, location)
      summaries  → Synthesized 1-2 sentence summaries per result
      passages   → Full retrieved text chunks

    The server retrieves many candidates internally, then returns
    only the top results at the requested detail level.
    """
```

**Token savings**: Default returns synthesized summaries, not raw book text.

### 3. Synthesis Before Return

```python
@mcp_tool
def get_advice(
    question: str,
    sources: list[str] | None = None,
    perspective: Literal["unified", "by_source", "compare"] = "unified",
    include_citations: bool = True
) -> AdviceResponse:
    """
    RAG with server-side synthesis.

    Internal flow:
      1. Embed question
      2. Retrieve 50-100 relevant chunks from vectors
      3. Retrieve related concepts from graph
      4. Use local model (or rules) to synthesize coherent advice
      5. Return ~500 tokens instead of ~10,000

    Perspectives:
      unified   → Single synthesized answer
      by_source → Grouped by book/author
      compare   → Highlight agreements and differences
    """
```

**Token savings**: 98%+ reduction by synthesizing in the server.

### 4. Knowledge Graph Traversal

```python
@mcp_tool
def trace_concept(
    concept: str,
    relationship: Literal["supports", "elaborates", "contradicts", "related"] | None = None,
    depth: int = 1,
    include_sources: bool = True
) -> ConceptGraph:
    """
    Traverse concept relationships.

    Example:
      trace_concept("emotion coaching", relationship="elaborates")
      → ["name it to tame it", "reflect feelings", "validate before redirect"]

    Each concept includes source citations if include_sources=True.
    """
```

### 5. Comparison Across Sources

```python
@mcp_tool
def compare_sources(
    topic: str,
    sources: list[str] | None = None,  # None = all sources
    aspect: Literal["philosophy", "strategies", "all"] = "all"
) -> ComparisonResult:
    """
    Compare how different sources approach a topic.

    Returns structured comparison:
      - Agreements: Where sources align
      - Differences: Where they diverge
      - Unique insights: What each source contributes
    """
```

---

## Data Models

### Book Metadata

```yaml
# knowledge/sources/{slug}/metadata.yaml
slug: good-inside
title: "Good Inside: A Guide to Becoming the Parent You Want to Be"
author: "Dr. Becky Kennedy"
short_name: "Good Inside"
isbn: "978-0063159488"
added_at: 2024-01-15
chapters:
  - number: 1
    title: "Good Inside"
    start_location: 100
    end_location: 450
  - number: 2
    title: "Building Connection Capital"
    start_location: 451
    end_location: 890
```

### Curated Content (Optional Enhancement)

```yaml
# knowledge/sources/{slug}/principles.yaml
principles:
  - id: gi-principle-001
    title: "Kids are good inside"
    summary: >
      Children's difficult behaviors are not evidence of a bad kid,
      but rather a good kid having a hard time.
    topics: [behavior, discipline, mindset]
    source:
      chapter: "Good Inside"
      location: 156
      quote: "Kids are good inside. Kids who lie are good inside..."
    concepts: [good-inside, behavior-as-communication]

  - id: gi-principle-002
    title: "Connection before correction"
    # ...
```

### Topic Registry

```yaml
# knowledge/topics/registry.yaml
topics:
  tantrums:
    display_name: "Tantrums & Meltdowns"
    description: "Handling emotional outbursts"
    related_topics: [emotions, discipline, regulation]

  sibling-conflict:
    display_name: "Sibling Conflict"
    description: "Managing fights between siblings"
    related_topics: [fairness, jealousy, conflict-resolution]
```

### Concept Relationships

```yaml
# knowledge/concepts/relationships.yaml
concepts:
  emotion-coaching:
    display_name: "Emotion Coaching"
    source: gottman-emotional-intelligence
    related:
      - concept: name-it-to-tame-it
        relationship: elaborates
        source: whole-brain-child
      - concept: sportscasting
        relationship: similar
        source: no-bad-kids

  name-it-to-tame-it:
    display_name: "Name It to Tame It"
    source: whole-brain-child
    related:
      - concept: emotion-coaching
        relationship: implements
        source: gottman-emotional-intelligence
```

---

## Storage Backends

### Vector Database: ChromaDB (Default)

```python
# Simple, embedded, no server required
import chromadb

client = chromadb.PersistentClient(path="storage/vectors")
collection = client.get_or_create_collection(
    name="book_chunks",
    metadata={"hnsw:space": "cosine"}
)
```

**Why ChromaDB:**
- Zero configuration, embedded
- Persists to disk
- Good enough for thousands of books
- Easy migration to pgvector later if needed

### Knowledge Graph: NetworkX (Default)

```python
# For small-medium libraries (< 10,000 concepts)
import networkx as nx
import pickle

G = nx.DiGraph()
G.add_edge("emotion-coaching", "name-it-to-tame-it",
           relationship="elaborates",
           source="whole-brain-child")

# Persist
with open("storage/graph/concepts.pickle", "wb") as f:
    pickle.dump(G, f)
```

**Upgrade path:** For larger libraries, swap to Neo4j with minimal code changes.

### Metadata: SQLite

```sql
CREATE TABLE books (
    slug TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chapters (
    id INTEGER PRIMARY KEY,
    book_slug TEXT REFERENCES books(slug),
    number INTEGER,
    title TEXT,
    start_location INTEGER,
    end_location INTEGER
);

CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    book_slug TEXT REFERENCES books(slug),
    chapter_id INTEGER REFERENCES chapters(id),
    content TEXT,
    start_location INTEGER,
    end_location INTEGER,
    embedding_id TEXT  -- Reference to ChromaDB
);
```

---

## Embedding Strategy

### Default: Sentence Transformers (Local)

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")  # Fast, 384 dims
# Or: "all-mpnet-base-v2" for better quality, 768 dims
```

### Optional: API-based

```python
# OpenAI
WYRD_EMBEDDING_PROVIDER=openai
WYRD_EMBEDDING_MODEL=text-embedding-3-small

# Voyage (optimized for retrieval)
WYRD_EMBEDDING_PROVIDER=voyage
WYRD_EMBEDDING_MODEL=voyage-3
```

---

## Synthesis Strategy

For the `get_advice` tool to synthesize results before returning:

### Option 1: Rule-based (No LLM Required)

```python
def synthesize_rule_based(chunks: list[Chunk], question: str) -> str:
    """
    Simple extraction and deduplication.
    Returns top chunks with source citations.
    """
    # Deduplicate similar content
    # Group by source
    # Format with citations
```

### Option 2: Local LLM via Ollama

```python
async def synthesize_with_ollama(chunks: list[Chunk], question: str) -> str:
    """
    Use small local model to synthesize.
    """
    prompt = f"""Based on these excerpts, answer the question concisely.

Question: {question}

Excerpts:
{format_chunks(chunks)}

Synthesize a helpful answer with citations."""

    response = await ollama.generate(model="llama3.2:3b", prompt=prompt)
    return response
```

### Option 3: Cloud LLM (User's API Key)

```python
# User provides their own API key
WYRD_SYNTHESIS_PROVIDER=anthropic
WYRD_SYNTHESIS_MODEL=claude-3-haiku-20240307
```

---

## Development Phases

### Phase 1: Core MVP

- [ ] Basic ePub ingestion → chunks → embeddings
- [ ] ChromaDB storage
- [ ] Simple semantic search
- [ ] MCP server with `search_knowledge` tool
- [ ] Docker packaging
- [ ] CLI: add, remove, list, serve

### Phase 2: Enhanced Retrieval

- [ ] Knowledge graph (NetworkX)
- [ ] `explore_library` with progressive discovery
- [ ] `trace_concept` for graph traversal
- [ ] Topic registry and tagging
- [ ] Hybrid search (vector + graph)

### Phase 3: Synthesis & Curation

- [ ] Server-side synthesis (rule-based)
- [ ] Optional Ollama integration for synthesis
- [ ] Human curation YAML format
- [ ] Curation import/validation
- [ ] `get_advice` with synthesis
- [ ] `compare_sources` tool

### Phase 4: Polish

- [ ] PDF support
- [ ] HTTP API transport
- [ ] Optional pgvector backend
- [ ] Optional Neo4j backend
- [ ] Comprehensive documentation
- [ ] Example curation templates

---

## References

- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-03-26)
- [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/toolkit/)
- [Production Python Docker with uv](https://hynek.me/articles/docker-uv/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)
