FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install Python deps from lockfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Install Chromium system deps explicitly.
# Playwright's --with-deps doesn't recognise Debian Trixie yet and tries to
# install Ubuntu 20.04 font packages (ttf-unifont, ttf-ubuntu-font-family)
# that don't exist on Trixie. We install deps manually instead.
# Package names reflect Trixie's time64 ABI transition (lib*t64 suffix).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2t64 \
    libatk-bridge2.0-0t64 \
    libatk1.0-0t64 \
    libcups2t64 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0t64 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    fonts-liberation \
    fonts-unifont \
    && rm -rf /var/lib/apt/lists/*

RUN uv run playwright install chromium

# App code
COPY . .
RUN mkdir -p data/discovery

CMD ["uv", "run", "python", "-m", "app.main", "--monitor"]
