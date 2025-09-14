#!/bin/bash
# AutoDropshipper VPS Deployment Script
# Optimized for VPS deployment with nginx and SSL

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VPS_MODE=false
SETUP_SSL=false
DOMAIN=""

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

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  --vps           Enable VPS mode with production settings"
    echo "  --ssl DOMAIN    Setup SSL certificate for DOMAIN (e.g., autodropshipper.mooo.com)"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Local development"
    echo "  $0 --vps              # VPS deployment without SSL"
    echo "  $0 --vps --ssl autodropshipper.mooo.com  # VPS with SSL"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --vps)
            VPS_MODE=true
            shift
            ;;
        --ssl)
            SETUP_SSL=true
            DOMAIN="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Setup SSL certificate with Let's Encrypt
setup_ssl() {
    if [ -z "$DOMAIN" ]; then
        print_error "Domain is required for SSL setup"
        return 1
    fi
    
    print_step "Setting up SSL certificate for $DOMAIN..."
    
    # Install certbot if not present
    if ! command -v certbot &> /dev/null; then
        print_info "Installing certbot..."
        sudo apt-get update
        sudo apt-get install -y certbot
    fi
    
    # Stop nginx temporarily to get certificate
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml stop nginx 2>/dev/null || true
    
    # Get certificate using standalone mode
    print_info "Obtaining SSL certificate from Let's Encrypt..."
    sudo certbot certonly --standalone \
        -d "$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email "admin@$DOMAIN" \
        --no-eff-email
    
    # Create certs directory if it doesn't exist
    mkdir -p ./nginx/certs
    
    # Copy certificates to nginx directory
    sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ./nginx/certs/
    sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ./nginx/certs/
    sudo chown $(whoami):$(whoami) ./nginx/certs/*.pem
    chmod 600 ./nginx/certs/*.pem
    
    # Update nginx config to use the domain and enable SSL
    print_info "Updating nginx configuration for SSL..."
    # Update server_name in nginx.conf
    sed -i "s/server_name .*/server_name $DOMAIN;/g" ./nginx/nginx.conf
    
    # Enable USE_SSL in environment
    if ! grep -q "USE_SSL=true" .env; then
        echo "USE_SSL=true" >> .env
    fi
    
    print_step "SSL certificate configured successfully"
    
    # Setup auto-renewal
    print_info "Setting up SSL auto-renewal..."
    (crontab -l 2>/dev/null | grep -v "certbot renew" ; echo "0 3 * * * certbot renew --quiet --deploy-hook 'docker-compose -f /opt/autodropshipper/docker-compose.yml -f /opt/autodropshipper/docker-compose.prod.yml restart nginx'") | crontab -
    print_info "SSL auto-renewal configured (daily at 3 AM)"
}

# Check system resources for VPS
check_vps_resources() {
    print_step "Checking VPS resources..."
    
    # Check available memory
    available_mem=$(free -m | awk 'NR==2{print $7}')
    if [ "$available_mem" -lt 1000 ]; then
        print_warning "Low memory available: ${available_mem}MB (recommended: 1000MB+)"
    else
        print_info "Available memory: ${available_mem}MB ✓"
    fi
    
    # Check available disk space
    available_disk=$(df -h / | awk 'NR==2{print $4}')
    print_info "Available disk space: ${available_disk}"
    
    # Check Docker installation
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed!"
        exit 1
    fi
}

# Main deployment process
main() {
    print_step "Starting AutoDropshipper deployment..."
    
    # Check environment file
    if [ "$VPS_MODE" = true ]; then
        if [ ! -f ".env.production" ]; then
            print_error ".env.production file not found!"
            print_warning "Please copy .env.production.example to .env.production and configure it"
            exit 1
        fi
        
        # Load production environment
        print_step "Loading production environment variables..."
        cp .env.production .env
        source .env
        
        # Create necessary directories
        mkdir -p logs/django
        mkdir -p nginx/certs
        print_info "Created necessary directories for logs and certificates"
        
        # Check VPS resources
        check_vps_resources
    else
        if [ ! -f ".env" ]; then
            print_error ".env file not found!"
            print_warning "Please create .env file with your configuration"
            exit 1
        fi
    fi
    
    # Pull latest changes from git
    print_step "Pulling latest changes from git..."
    git pull origin release/production-ready || print_warning "Could not pull from git, continuing with local version"
    
    # Stop existing containers
    print_step "Stopping existing containers..."
    if [ "$VPS_MODE" = true ]; then
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
    else
        docker-compose down
    fi
    
    # Build images
    print_step "Building Docker images..."
    if [ "$VPS_MODE" = true ]; then
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
    else
        docker-compose build
    fi
    
    # Start database
    print_step "Starting database service..."
    if [ "$VPS_MODE" = true ]; then
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d db
    else
        docker-compose up -d db
    fi
    
    # Wait for database
    print_step "Waiting for database to be ready..."
    sleep 10
    
    # Run migrations
    print_step "Running database migrations..."
    if [ "$VPS_MODE" = true ]; then
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm webapp-prod uv run python webapp/manage.py migrate
    else
        docker-compose run --rm webapp uv run python webapp/manage.py migrate
    fi
    
    # Collect static files
    print_step "Collecting static files..."
    if [ "$VPS_MODE" = true ]; then
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm webapp-prod uv run python webapp/manage.py collectstatic --noinput
    else
        docker-compose run --rm webapp uv run python webapp/manage.py collectstatic --noinput
    fi
    
    # Setup SSL if requested (before starting nginx)
    if [ "$SETUP_SSL" = true ] && [ "$VPS_MODE" = true ]; then
        setup_ssl
    fi
    
    # Start all services
    print_step "Starting all services..."
    if [ "$VPS_MODE" = true ]; then
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    else
        docker-compose up -d webapp
    fi
    
    # Wait for services to be ready
    sleep 5
    
    # Show running containers
    print_step "Deployment complete! Running containers:"
    if [ "$VPS_MODE" = true ]; then
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
    else
        docker-compose ps
    fi
    
    # Show access information
    echo ""
    print_step "✅ Deployment successful!"
    echo ""
    
    if [ "$VPS_MODE" = true ]; then
        if [ -n "$DOMAIN" ] && [ "$SETUP_SSL" = true ]; then
            echo "🌐 Access your application at: https://$DOMAIN"
            echo "🔒 SSL/HTTPS is enabled"
        elif [ -n "$DOMAIN" ]; then
            echo "🌐 Access your application at: http://$DOMAIN"
            echo "⚠️  SSL not configured. Run with --ssl flag to enable HTTPS"
        elif [ -n "$ALLOWED_HOSTS" ]; then
            VPS_IP="${ALLOWED_HOSTS%%,*}"
            echo "🌐 Access your application at: http://$VPS_IP"
        else
            echo "🌐 Access your application at: http://74.208.197.137"
        fi
        echo "📊 View logs: docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f"
        echo "🔄 Restart: docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart"
        
        # Cron reminder
        if ! crontab -l 2>/dev/null | grep -q "scheduler.sh"; then
            echo ""
            print_warning "Don't forget to set up the cron jobs for automated scraping!"
            echo "Add these lines to your crontab (crontab -e):"
            echo "0 6 * * * /opt/autodropshipper/scheduler.sh"
            echo "0 13 * * * /opt/autodropshipper/scheduler.sh"
            echo "0 19 * * * /opt/autodropshipper/scheduler.sh"
        fi
    else
        echo "🌐 Access your application at: http://localhost:8000"
        echo "📊 View logs: docker-compose logs -f webapp"
        echo "🔄 Restart: docker-compose restart webapp"
    fi
    
    echo ""
    print_info "Deployment mode: $([ "$VPS_MODE" = true ] && echo "VPS Production" || echo "Local Development")"
    [ "$SETUP_SSL" = true ] && [ -n "$DOMAIN" ] && print_info "SSL: Enabled for $DOMAIN ✓"
}

# Run main function
main