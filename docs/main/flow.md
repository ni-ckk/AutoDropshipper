# FLOW - Application Architecture & Process Flow

This document describes the mid-level architecture and process flow. 
Please always include schematic flow visualization.


# 🚀 Quick Launch Guide

  Docker Setup & Launch

  1. Start the database and web app:
  docker-compose up -d db webapp

  2. Run database migrations (first time only):
  docker-compose run webapp uv run python webapp/manage.py migrate

  3. Access the Django dashboard:
  - Open http://localhost:8000

  Running Scrapers in Docker

  Test Idealo scraper (no database save):
  docker-compose run scrapers uv run python -m src.scrapers.main --scope idealo

  Test eBay scraper with a query:
  docker-compose run scrapers uv run python -m src.scrapers.main --scope ebay --query "PS5"

  Run full production flow (Idealo → DB → eBay → DB):
  docker-compose run scrapers uv run python -m src.scrapers.main --scope full

  Quick Test Aliases

  The docker-compose.yml includes pre-configured test services:
  docker-compose run test-idealo    # Tests idealo scraping
  docker-compose run test-ebay       # Tests eBay with "PS5 Pro" query
  docker-compose run production      # Runs full production flow

  Local Development Testing

  Setup for local testing:
  # Install UV if not already installed (Windows Git Bash)
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Setup scrapers
  cd src && uv sync

  # Setup webapp
  cd ../webapp && uv sync

  Run local tests:
  # Test scrapers
  cd src
  uv run pytest                      # Run all tests
  uv run pytest -v                   # Verbose output
  uv run python test_idealo_local.py # Local idealo test
  uv run python test_ebay_local.py   # Local eBay test

  # Test webapp
  cd webapp
  uv run pytest

  Code quality checks:
  # Format code
  cd src && uv run ruff format .

  # Check linting
  cd src && uv run ruff check .

  # Type checking
  cd src && uv run mypy .

  Environment Variables

  Make sure you have a .env file with:
  - POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
  - SCRAPE_URL_IDEALO (Idealo search URL)
  - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (for notifications)
  - SECRET_KEY (for Django)


## Architecture Overview

## Application Startup Flow

## User Interaction Flow

etc.