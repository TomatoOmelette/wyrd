# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /bin/uv

# Set up working directory
WORKDIR /app

# Copy dependency files first (for layer caching)
COPY pyproject.toml uv.lock* ./

# Install dependencies (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --compile-bytecode || \
    uv sync --no-install-project --compile-bytecode

# Copy source code
COPY src/ ./src/

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --compile-bytecode || \
    uv sync --compile-bytecode

# Runtime stage
FROM python:3.12-slim AS runtime

# Install runtime dependencies for sentence-transformers and other native libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Set up PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Create directories for user content and storage
RUN mkdir -p /app/knowledge /app/storage

# Default environment variables
ENV WYRD_EMBEDDING_MODEL=all-MiniLM-L6-v2
ENV WYRD_STORAGE_PATH=/app/storage
ENV WYRD_KNOWLEDGE_PATH=/app/knowledge

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import wyrd; print('ok')" || exit 1

# Default: MCP server mode (stdio)
ENTRYPOINT ["python", "-m", "wyrd"]
CMD ["serve", "--transport", "stdio"]
