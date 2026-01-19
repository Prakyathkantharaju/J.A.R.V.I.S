#!/bin/bash
# JARVIS - Raspberry Pi 4 Setup Script
# Pi 4 is the "Data" node - runs Home Assistant, database, Redis

set -e

echo "🤖 Setting up JARVIS on Raspberry Pi 4 (Data)..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
JARVIS_DIR="/opt/jarvis"
DATA_DIR="/var/lib/jarvis"
LOG_DIR="/var/log/jarvis"
CONFIG_DIR="/etc/jarvis"
HA_DIR="/opt/homeassistant"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# System updates
echo -e "${YELLOW}Updating system...${NC}"
apt update && apt upgrade -y

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
apt install -y \
    docker.io \
    docker-compose \
    redis-server \
    curl \
    git

# Enable Docker
systemctl enable docker
systemctl start docker

# Add pi user to docker group
usermod -aG docker pi

# Create directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p "$JARVIS_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$HA_DIR"

# Clone or update repository
if [ -d "$JARVIS_DIR/.git" ]; then
    echo -e "${YELLOW}Updating JARVIS...${NC}"
    cd "$JARVIS_DIR"
    git pull
else
    echo -e "${YELLOW}Cloning JARVIS...${NC}"
    git clone https://github.com/prakyath/life-os.git "$JARVIS_DIR"
fi

cd "$JARVIS_DIR"

# Set up Home Assistant via Docker
echo -e "${YELLOW}Setting up Home Assistant...${NC}"
cat > "$HA_DIR/docker-compose.yml" << 'EOF'
version: '3'
services:
  homeassistant:
    container_name: homeassistant
    image: "ghcr.io/home-assistant/home-assistant:stable"
    volumes:
      - /opt/homeassistant/config:/config
      - /etc/localtime:/etc/localtime:ro
      - /run/dbus:/run/dbus:ro
    restart: unless-stopped
    privileged: true
    network_mode: host
EOF

mkdir -p "$HA_DIR/config"

# Start Home Assistant
cd "$HA_DIR"
docker-compose up -d

# Configure Redis
echo -e "${YELLOW}Configuring Redis...${NC}"
cat > /etc/redis/redis.conf << 'EOF'
bind 0.0.0.0
port 6379
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
dir /var/lib/redis
EOF

systemctl enable redis-server
systemctl restart redis-server

# Create SQLite database directory
mkdir -p "$DATA_DIR/db"
chown -R pi:pi "$DATA_DIR"

# Install systemd service for data sync receiver
cat > /etc/systemd/system/jarvis-data.service << EOF
[Unit]
Description=JARVIS Data Service
After=network.target redis.service docker.service

[Service]
Type=simple
User=pi
WorkingDirectory=$JARVIS_DIR
ExecStart=/usr/bin/echo "Data service placeholder"
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  Pi 4 (Data) setup complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo "Services running:"
echo "  - Home Assistant: http://$(hostname -I | awk '{print $1}'):8123"
echo "  - Redis: $(hostname -I | awk '{print $1}'):6379"
echo ""
echo "Next steps:"
echo "  1. Complete Home Assistant onboarding in browser"
echo "  2. Install HA Companion App on your phone"
echo "  3. Create a long-lived access token in HA"
echo "  4. Update Pi 5 config with HA URL and token"
echo ""
echo "Check Home Assistant logs: docker logs -f homeassistant"
echo ""
