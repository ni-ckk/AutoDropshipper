#!/bin/bash
# AutoDropshipper VPS Initial Setup Script
# For Ubuntu 22.04 on IONOS VPS (4GB RAM, 2 CPUs)
# Note: IONOS firewall is managed through their control panel

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/autodropshipper"
SWAP_SIZE="4G"
GITHUB_REPO="https://github.com/yourusername/AutoDropshipper.git"  # Update this

# Function to print colored output
print_step() {
    echo -e "${GREEN}[SETUP]${NC} $1"
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

# Check if running as root or with sudo
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        print_error "Please run this script with sudo or as root"
        exit 1
    fi
}

# Update system packages
update_system() {
    print_step "Updating system packages..."
    apt-get update
    apt-get upgrade -y
    print_info "System packages updated"
}

# Install essential packages
install_essentials() {
    print_step "Installing essential packages..."
    apt-get install -y \
        curl \
        wget \
        git \
        vim \
        htop \
        net-tools \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        unzip \
        build-essential \
        python3-pip \
        certbot  # For SSL certificates
    
    print_info "Essential packages installed"
}

# Setup swap file for memory management
setup_swap() {
    print_step "Setting up swap file ($SWAP_SIZE)..."
    
    # Check if swap already exists
    if [ -f /swapfile ]; then
        print_warning "Swap file already exists, skipping..."
        return
    fi
    
    # Create swap file
    fallocate -l $SWAP_SIZE /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    
    # Make swap permanent
    if ! grep -q "/swapfile" /etc/fstab; then
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
    
    # Optimize swappiness for server use
    sysctl vm.swappiness=10
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
    
    print_info "Swap file created and activated"
    free -h
}

# Install Docker
install_docker() {
    print_step "Installing Docker..."
    
    # Check if Docker is already installed
    if command -v docker &> /dev/null; then
        print_warning "Docker is already installed"
        docker --version
        return
    fi
    
    # Install Docker using official script
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    
    # Add current user to docker group (if not root)
    if [ "$SUDO_USER" ]; then
        usermod -aG docker $SUDO_USER
        print_info "Added $SUDO_USER to docker group"
    fi
    
    # Enable and start Docker
    systemctl enable docker
    systemctl start docker
    
    print_info "Docker installed successfully"
    docker --version
}

# Install Docker Compose
install_docker_compose() {
    print_step "Installing Docker Compose..."
    
    # Check if Docker Compose is already installed
    if command -v docker-compose &> /dev/null; then
        print_warning "Docker Compose is already installed"
        docker-compose --version
        return
    fi
    
    # Install Docker Compose V2 as Docker plugin
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    
    # Also install standalone version for compatibility
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    print_info "Docker Compose installed successfully"
    docker-compose --version
}

# Setup application directory
setup_app_directory() {
    print_step "Setting up application directory..."
    
    # Create application directory
    mkdir -p $APP_DIR
    
    # Set ownership to the sudo user if available
    if [ "$SUDO_USER" ]; then
        chown -R $SUDO_USER:$SUDO_USER $APP_DIR
        print_info "Application directory created at $APP_DIR with ownership set to $SUDO_USER"
    else
        print_info "Application directory created at $APP_DIR"
    fi
}

# Setup automatic security updates
setup_auto_updates() {
    print_step "Setting up automatic security updates..."
    
    # Install unattended-upgrades
    apt-get install -y unattended-upgrades apt-listchanges
    
    # Configure automatic updates
    cat > /etc/apt/apt.conf.d/50unattended-upgrades <<EOF
Unattended-Upgrade::Allowed-Origins {
    "\${distro_id}:\${distro_codename}-security";
    "\${distro_id}ESMApps:\${distro_codename}-apps-security";
    "\${distro_id}ESM:\${distro_codename}-infra-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Automatic-Reboot-Time "03:00";
EOF
    
    # Enable automatic updates
    cat > /etc/apt/apt.conf.d/20auto-upgrades <<EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF
    
    print_info "Automatic security updates configured"
}

# Setup system monitoring
setup_monitoring() {
    print_step "Setting up system monitoring..."
    
    # Install monitoring tools
    apt-get install -y \
        iotop \
        iftop \
        ncdu \
        glances
    
    # Setup log rotation for Docker
    cat > /etc/docker/daemon.json <<EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "5"
    }
}
EOF
    
    # Restart Docker to apply log rotation
    systemctl restart docker
    
    print_info "System monitoring tools installed"
}

# Setup fail2ban for SSH protection
setup_fail2ban() {
    print_step "Setting up fail2ban for SSH protection..."
    
    apt-get install -y fail2ban
    
    # Configure fail2ban for SSH
    cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF
    
    # Enable and start fail2ban
    systemctl enable fail2ban
    systemctl start fail2ban
    
    print_info "fail2ban configured for SSH protection"
}

# Clone application repository
clone_repository() {
    print_step "Ready to clone repository..."
    
    echo ""
    print_warning "Please update the GITHUB_REPO variable in this script first!"
    print_info "Current value: $GITHUB_REPO"
    echo ""
    read -p "Do you want to clone the repository now? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd $APP_DIR
        
        # Check if directory is empty
        if [ "$(ls -A $APP_DIR)" ]; then
            print_warning "Directory $APP_DIR is not empty. Skipping clone."
        else
            print_info "Cloning repository..."
            if [ "$SUDO_USER" ]; then
                sudo -u $SUDO_USER git clone $GITHUB_REPO .
            else
                git clone $GITHUB_REPO .
            fi
            print_info "Repository cloned successfully"
        fi
    else
        print_info "Skipping repository clone. You can clone it manually later:"
        echo "cd $APP_DIR && git clone $GITHUB_REPO ."
    fi
}

# Setup cron jobs
setup_cron() {
    print_step "Setting up cron jobs..."
    
    CRON_FILE="/etc/cron.d/autodropshipper"
    
    cat > $CRON_FILE <<EOF
# AutoDropshipper scheduled runs
# Runs 3 times daily with random delay handled by scheduler.sh
0 6 * * * root $APP_DIR/scheduler.sh >> /var/log/autodropshipper-cron.log 2>&1
0 13 * * * root $APP_DIR/scheduler.sh >> /var/log/autodropshipper-cron.log 2>&1
0 19 * * * root $APP_DIR/scheduler.sh >> /var/log/autodropshipper-cron.log 2>&1

# SSL certificate renewal (if using Let's Encrypt)
0 3 * * * root certbot renew --quiet --deploy-hook "cd $APP_DIR && docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx" >> /var/log/letsencrypt-renew.log 2>&1
EOF
    
    chmod 644 $CRON_FILE
    
    # Create log file with proper permissions
    touch /var/log/autodropshipper-cron.log
    chmod 666 /var/log/autodropshipper-cron.log
    
    print_info "Cron jobs configured"
}

# Final system optimizations
system_optimizations() {
    print_step "Applying system optimizations..."
    
    # Increase file descriptor limits
    cat >> /etc/security/limits.conf <<EOF

# AutoDropshipper limits
* soft nofile 65536
* hard nofile 65536
* soft nproc 32768
* hard nproc 32768
EOF
    
    # Network optimizations for web server
    cat >> /etc/sysctl.conf <<EOF

# Network optimizations for AutoDropshipper
net.core.somaxconn = 65536
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
net.ipv4.ip_local_port_range = 10000 65000
EOF
    
    # Apply sysctl settings
    sysctl -p
    
    print_info "System optimizations applied"
}

# Print summary
print_summary() {
    echo ""
    echo "=================================================="
    print_step "VPS Setup Complete!"
    echo "=================================================="
    echo ""
    print_info "System Information:"
    echo "  - OS: $(lsb_release -ds)"
    echo "  - Kernel: $(uname -r)"
    echo "  - Docker: $(docker --version)"
    echo "  - Docker Compose: $(docker-compose --version)"
    echo "  - Memory: $(free -h | awk 'NR==2{print $2}') total"
    echo "  - Swap: $SWAP_SIZE configured"
    echo "  - Application directory: $APP_DIR"
    echo ""
    print_info "Security:"
    echo "  - Automatic security updates: Enabled"
    echo "  - fail2ban: Configured for SSH"
    echo "  - Firewall: Managed via IONOS control panel"
    echo ""
    print_info "Next Steps:"
    echo "  1. Configure IONOS firewall (ports 22, 80, 443)"
    echo "  2. Clone your repository to $APP_DIR"
    echo "  3. Copy .env.production.example to .env.production"
    echo "  4. Run: cd $APP_DIR && ./deploy.sh --vps --ssl yourdomain.com"
    echo ""
    print_warning "Remember to:"
    echo "  - Update DNS records for your domain"
    echo "  - Configure environment variables in .env.production"
    echo "  - Test the deployment thoroughly"
    echo ""
    
    if [ "$SUDO_USER" ]; then
        print_warning "Log out and back in for docker group changes to take effect for user: $SUDO_USER"
    fi
}

# Main execution
main() {
    print_step "Starting VPS setup for AutoDropshipper..."
    echo "Server: IONOS VPS (4GB RAM, 2 CPUs)"
    echo "OS: Ubuntu 22.04"
    echo ""
    
    # Confirm before proceeding
    read -p "Do you want to continue with the setup? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Setup cancelled"
        exit 0
    fi
    
    check_root
    update_system
    install_essentials
    setup_swap
    install_docker
    install_docker_compose
    setup_app_directory
    setup_auto_updates
    setup_monitoring
    setup_fail2ban
    system_optimizations
    clone_repository
    setup_cron
    print_summary
}

# Run main function
main