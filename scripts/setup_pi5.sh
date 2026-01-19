#!/bin/bash
# JARVIS - Raspberry Pi 5 Setup Script
# Pi 5 is the "Brain" - runs MCP server, voice, and sync

set -e

echo "🤖 Setting up JARVIS on Raspberry Pi 5 (Brain)..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
JARVIS_DIR="/opt/jarvis"
JARVIS_USER="jarvis"
DATA_DIR="/var/lib/jarvis"
LOG_DIR="/var/log/jarvis"
CONFIG_DIR="/etc/jarvis"

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
    python3.12 \
    python3.12-venv \
    python3-pip \
    git \
    curl \
    bluetooth \
    bluez \
    bluez-tools \
    pulseaudio \
    pulseaudio-module-bluetooth \
    portaudio19-dev \
    libffi-dev \
    libssl-dev

# Install uv
echo -e "${YELLOW}Installing uv...${NC}"
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.cargo/bin:$PATH"

# Create jarvis user if doesn't exist
if ! id "$JARVIS_USER" &>/dev/null; then
    echo -e "${YELLOW}Creating jarvis user...${NC}"
    useradd -r -s /bin/false -d "$DATA_DIR" "$JARVIS_USER"
    usermod -a -G audio,bluetooth "$JARVIS_USER"
fi

# Create directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p "$JARVIS_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$CONFIG_DIR"

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

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
uv sync --extra voice

# Copy configuration
if [ ! -f "$CONFIG_DIR/config.env" ]; then
    cp .env.example "$CONFIG_DIR/config.env"
    echo -e "${YELLOW}Created config file at $CONFIG_DIR/config.env${NC}"
    echo -e "${YELLOW}Please edit with your credentials!${NC}"
fi

# Link config
ln -sf "$CONFIG_DIR/config.env" "$JARVIS_DIR/.env"

# Set up Bluetooth audio
echo -e "${YELLOW}Configuring Bluetooth audio...${NC}"
cat > /etc/bluetooth/main.conf << 'EOF'
[General]
Class = 0x200414
DiscoverableTimeout = 0
Enable=Source,Sink,Media,Socket

[Policy]
AutoEnable=true
EOF

# Enable Bluetooth service
systemctl enable bluetooth
systemctl start bluetooth

# Set up PulseAudio for system-wide
cat > /etc/pulse/system.pa << 'EOF'
load-module module-bluetooth-policy
load-module module-bluetooth-discover
load-module module-native-protocol-unix auth-anonymous=1
EOF

# Install systemd services
echo -e "${YELLOW}Installing systemd services...${NC}"
cp deploy/systemd/jarvis-voice.service /etc/systemd/system/
cp deploy/systemd/jarvis-sync.service /etc/systemd/system/

# Set ownership
chown -R "$JARVIS_USER:$JARVIS_USER" "$DATA_DIR"
chown -R "$JARVIS_USER:$JARVIS_USER" "$LOG_DIR"

# Reload systemd
systemctl daemon-reload

# Enable services
systemctl enable jarvis-voice
systemctl enable jarvis-sync

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  Pi 5 (Brain) setup complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit $CONFIG_DIR/config.env with your credentials"
echo "  2. Pair Bluetooth speaker: bluetoothctl"
echo "  3. Start services: sudo systemctl start jarvis-voice jarvis-sync"
echo "  4. Check logs: journalctl -u jarvis-voice -f"
echo ""
