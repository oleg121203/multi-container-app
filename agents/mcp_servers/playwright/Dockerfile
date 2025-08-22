# Dockerfile for Playwright MCP Server
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Install system dependencies for MCP server
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    playwright==1.40.0 \
    pydantic==2.5.0 \
    aiohttp==3.9.1

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps

# Copy MCP server code
COPY server.py .

# Create non-root user with proper permissions
RUN useradd -m -s /bin/bash playwright \
    && mkdir -p /app/screenshots \
    && chown -R playwright:playwright /app

USER playwright

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:4001/health || exit 1

# Expose port
EXPOSE 4001

# Run the MCP server
CMD ["python", "server.py"]