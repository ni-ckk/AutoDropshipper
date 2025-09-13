#!/bin/bash
# AutoDropshipper Production Scheduler
# Runs the production scraping flow with a random delay (0-59 minutes)
# This script should be called by cron at the start of each time window

# Configuration
PROJECT_DIR="/home/$(whoami)/AutoDropshipper"  # Update this path to your project location
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/scheduler_$(date +%Y%m%d).log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Generate random delay between 0 and 3599 seconds (0-59 minutes)
DELAY=$((RANDOM % 3600))
DELAY_MINUTES=$((DELAY / 60))
DELAY_SECONDS=$((DELAY % 60))

log_message "Starting scheduler - will run after ${DELAY_MINUTES}m ${DELAY_SECONDS}s delay"

# Sleep for random delay
sleep $DELAY

log_message "Starting production scraping flow"

# Run the production flow using docker-compose
# Using --rm to remove the container after execution
docker-compose run --rm production 2>&1 | tee -a "$LOG_FILE"

# Check exit status
if [ $? -eq 0 ]; then
    log_message "Production flow completed successfully"
else
    log_message "ERROR: Production flow failed with exit code $?"
fi

log_message "Scheduler run completed"
log_message "----------------------------------------"