FROM python:3.12-slim

LABEL maintainer="Hansel Wahjono"
LABEL description="AEO-CLI: Audit URLs for AI crawler readiness"

WORKDIR /app

# Install system deps for crawl4ai (headless browser)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install aeo-cli
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Install browser for crawl4ai (optional, for content analysis)
RUN crawl4ai-setup 2>/dev/null || echo "Browser setup skipped"

ENTRYPOINT ["aeo-cli"]
CMD ["--help"]
