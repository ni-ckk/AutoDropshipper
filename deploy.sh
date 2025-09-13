#!/bin/bash
# AutoDropshipper Deployment Script
# One-command deployment for production environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${GREEN}[DEPLOY]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    print_error ".env.production file not found!"
    print_warning "Please copy .env.production.example to .env.production and configure it"
    exit 1
fi

# Load production environment variables
print_step "Loading production environment variables..."
cp .env.production .env

# Pull latest changes from git
print_step "Pulling latest changes from git..."
git pull origin main || git pull origin master || print_warning "Could not pull from git, continuing with local version"

# Stop existing containers
print_step "Stopping existing containers..."
docker-compose down

# Build new images
print_step "Building Docker images..."
docker-compose build

# Start database first
print_step "Starting database service..."
docker-compose up -d db

# Wait for database to be ready
print_step "Waiting for database to be ready..."
sleep 5

# Run database migrations
print_step "Running database migrations..."
docker-compose run --rm webapp-prod uv run python webapp/manage.py migrate

# Collect static files
print_step "Collecting static files..."
docker-compose run --rm webapp-prod uv run python webapp/manage.py collectstatic --noinput

# Start production services
print_step "Starting production services..."
docker-compose up -d webapp-prod

# Show running containers
print_step "Deployment complete! Running containers:"
docker-compose ps

# Show logs from last 10 lines
print_step "Recent logs from webapp:"
docker-compose logs --tail=10 webapp-prod

print_step "✅ Deployment successful!"
echo ""
echo "🌐 Access your application at: http://localhost:8000"
echo "📊 View logs with: docker-compose logs -f webapp-prod"
echo "🔄 Restart services with: docker-compose restart webapp-prod"
echo ""

# Setup cron reminder
if ! crontab -l 2>/dev/null | grep -q "scheduler.sh"; then
    print_warning "Don't forget to set up the cron jobs for automated scraping!"
    echo "Add these lines to your crontab (crontab -e):"
    echo "0 6 * * * $PWD/scheduler.sh"
    echo "0 13 * * * $PWD/scheduler.sh"
    echo "0 19 * * * $PWD/scheduler.sh"
fi