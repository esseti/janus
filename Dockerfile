FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (cached layer — only re-runs when pyproject.toml/uv.lock change)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache

# Copy source code
COPY src/ ./src/

# Runtime data (secrets, state files, user config) must be mounted at /data.
# Set via JANUS_DATA_DIR so the app reads everything from that path.
ENV JANUS_DATA_DIR=/data
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "src.main"]
