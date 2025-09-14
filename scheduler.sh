#!/bin/bash
# AutoDropshipper VPS Production Scheduler
# Runs the production scraping flow with a random delay (0-59 minutes)
# This script should be called by cron at the start of each time window
# Optimized for VPS deployment with resource checking

# Configuration
PROJECT_DIR="/opt/autodropshipper"  # Standard VPS application path
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/scheduler_$(date +%Y%m%d).log"
MAX_LOG_SIZE=104857600  # 100MB max log size

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to rotate logs if they get too large
rotate_logs() {
    if [ -f "$LOG_FILE" ]; then
        file_size=$(stat -c%s "$LOG_FILE" 2>/dev/null || stat -f%z "$LOG_FILE" 2>/dev/null || echo 0)
        if [ "$file_size" -gt "$MAX_LOG_SIZE" ]; then
            log_message "Rotating large log file ($(du -h $LOG_FILE | cut -f1))"
            mv "$LOG_FILE" "${LOG_FILE}.$(date +%Y%m%d_%H%M%S)"
            # Keep only last 5 rotated logs
            ls -t "${LOG_DIR}"/scheduler_*.log.* 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null
        fi
    fi
}

# Function to check available memory
check_memory() {
    available_mem=$(free -m | awk 'NR==2{print $7}')
    if [ "$available_mem" -lt 1500 ]; then
        log_message "WARNING: Low memory available: ${available_mem}MB (required: 1500MB)"
        log_message "Waiting for memory to free up..."
        
        # Try to free some memory
        sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
        
        # Wait and recheck
        sleep 300  # Wait 5 minutes
        
        # Recheck memory
        available_mem=$(free -m | awk 'NR==2{print $7}')
        if [ "$available_mem" -lt 1000 ]; then
            log_message "ERROR: Still insufficient memory: ${available_mem}MB. Aborting."
            exit 1
        fi
    fi
    log_message "Available memory: ${available_mem}MB ✓"
}

# Function to check if another instance is running
check_running_instance() {
    if docker ps | grep -q "autodropshipper_production"; then
        log_message "WARNING: Another production instance is already running. Skipping this run."
        exit 0
    fi
}

# Main execution
main() {
    # Rotate logs if needed
    rotate_logs
    
    log_message "========================================"
    log_message "Starting VPS scheduler"
    
    # Change to project directory
    if [ ! -d "$PROJECT_DIR" ]; then
        log_message "ERROR: Project directory not found: $PROJECT_DIR"
        exit 1
    fi
    cd "$PROJECT_DIR" || exit 1
    
    # Check if docker-compose files exist
    if [ ! -f "docker-compose.yml" ] || [ ! -f "docker-compose.prod.yml" ]; then
        log_message "ERROR: Docker compose files not found"
        exit 1
    fi
    
    # Check for running instances
    check_running_instance
    
    # Check available memory
    check_memory
    
    # Generate random delay between 0 and 3599 seconds (0-59 minutes)
    DELAY=$((RANDOM % 3600))
    DELAY_MINUTES=$((DELAY / 60))
    DELAY_SECONDS=$((DELAY % 60))
    
    log_message "Will run after ${DELAY_MINUTES}m ${DELAY_SECONDS}s delay"
    
    # Sleep for random delay
    sleep $DELAY
    
    log_message "Starting production scraping flow"
    
    # Load production environment
    if [ -f ".env.production" ]; then
        export $(grep -v '^#' .env.production | xargs)
    fi
    
    # Run the production flow using docker-compose with production override
    # Using --rm to remove the container after execution
    # Adding timeout to prevent hung processes
    timeout 7200 docker-compose \
        -f docker-compose.yml \
        -f docker-compose.prod.yml \
        run --rm production 2>&1 | tee -a "$LOG_FILE"
    
    EXIT_CODE=$?
    
    # Check exit status
    if [ $EXIT_CODE -eq 0 ]; then
        log_message "✓ Production flow completed successfully"
        
        # Log resource usage
        log_message "Current memory usage:"
        free -h | head -3 | sed 's/^/  /' | tee -a "$LOG_FILE"
        
        log_message "Docker container stats:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -5 | sed 's/^/  /' | tee -a "$LOG_FILE"
    elif [ $EXIT_CODE -eq 124 ]; then
        log_message "ERROR: Production flow timed out after 2 hours"
        # Try to clean up
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
    else
        log_message "ERROR: Production flow failed with exit code $EXIT_CODE"
    fi
    
    log_message "Scheduler run completed"
    log_message "========================================"
}

# Run main function
main