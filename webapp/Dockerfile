FROM python:3.13.5-bookworm

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev --no-install-recommends

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
