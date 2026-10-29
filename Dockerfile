FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_TRUSTED_HOST="pypi.org files.pythonhosted.org pypi.python.org github.com objects.githubusercontent.com raw.githubusercontent.com" \
    NODE_TLS_REJECT_UNAUTHORIZED=0

WORKDIR /app

# Install system utilities and Playwright runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    libpq-dev \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements with SSL-bypass for proxy/corporate environments
COPY requirements.txt .
COPY wheels/ ./wheels/
RUN pip config set global.trusted-host "pypi.org files.pythonhosted.org pypi.python.org" && \
    pip install --no-cache-dir \
        --trusted-host pypi.org \
        --trusted-host files.pythonhosted.org \
        --trusted-host pypi.python.org \
        -U pip setuptools wheel && \
    pip install --no-cache-dir \
        --trusted-host pypi.org \
        --trusted-host files.pythonhosted.org \
        --trusted-host pypi.python.org \
        -r requirements.txt && \
    pip install --no-cache-dir ./wheels/en_core_web_sm-3.8.0-py3-none-any.whl && \
    rm -rf ./wheels

# Install Playwright browser binary
RUN NODE_TLS_REJECT_UNAUTHORIZED=0 playwright install chromium



# Copy application source code
COPY . .


# Create persistent storage directories
RUN mkdir -p /app/data/snapshots /app/data/exports /app/secrets

EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

