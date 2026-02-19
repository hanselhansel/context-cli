FROM python:3.12-slim

LABEL maintainer="Hansel Wahjono"
LABEL description="Context CLI: Lint URLs for LLM readiness and token efficiency"

WORKDIR /app

# Install system deps for crawl4ai (headless browser)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install context-cli
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Install browser for crawl4ai (optional, for content analysis)
RUN crawl4ai-setup 2>/dev/null || echo "Browser setup skipped"

ENTRYPOINT ["context-cli"]
CMD ["--help"]
