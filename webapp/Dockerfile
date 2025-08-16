FROM python:3.13.5-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# copy project dependency files  
COPY pyproject.toml uv.lock ./

# install Python dependencies using UV
RUN uv sync --frozen --no-cache

# copy webapp source code
COPY . ./webapp/

# expose port  
EXPOSE 8000
