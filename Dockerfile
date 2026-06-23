FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install Python deps from lockfile (cached layer — only rebuilds when lock changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Install Playwright + all system deps for the current Debian version
# (handles libasound2 vs libasound2t64 automatically)
RUN uv run playwright install --with-deps chromium

# App code
COPY . .
RUN mkdir -p data/discovery

CMD ["uv", "run", "python", "-m", "app.main", "--monitor"]
