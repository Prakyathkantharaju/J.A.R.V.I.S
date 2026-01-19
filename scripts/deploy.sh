#!/bin/bash
# JARVIS - Remote Deployment Script
# Deploy to Raspberry Pis from development machine

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Load config from .env if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

PI5_HOST="${PI5_HOST:-pi5.local}"
PI5_USER="${PI5_USER:-pi}"
PI4_HOST="${PI4_HOST:-pi4.local}"
PI4_USER="${PI4_USER:-pi}"

usage() {
    echo "Usage: $0 <target> [options]"
    echo ""
    echo "Targets:"
    echo "  pi5          Deploy to Pi 5 (Brain)"
    echo "  pi4          Deploy to Pi 4 (Data)"
    echo "  all          Deploy to both Pis"
    echo "  sync         Sync code only (no setup)"
    echo ""
    echo "Options:"
    echo "  --setup      Run full setup script on target"
    echo "  --restart    Restart services after deploy"
    echo ""
    echo "Environment variables (or set in .env):"
    echo "  PI5_HOST     Pi 5 hostname (default: pi5.local)"
    echo "  PI5_USER     Pi 5 username (default: pi)"
    echo "  PI4_HOST     Pi 4 hostname (default: pi4.local)"
    echo "  PI4_USER     Pi 4 username (default: pi)"
}

sync_to_pi() {
    local host=$1
    local user=$2

    echo -e "${YELLOW}Syncing code to $user@$host...${NC}"

    rsync -avz --delete \
        --exclude '.git' \
        --exclude '.venv' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.env' \
        --exclude 'node_modules' \
        ./ "$user@$host:/opt/jarvis/"

    echo -e "${GREEN}✓ Code synced to $host${NC}"
}

deploy_pi5() {
    local setup=$1
    local restart=$2

    echo -e "${YELLOW}Deploying to Pi 5 (Brain)...${NC}"

    # Check connectivity
    if ! ping -c 1 "$PI5_HOST" &> /dev/null; then
        echo -e "${RED}Cannot reach $PI5_HOST${NC}"
        exit 1
    fi

    sync_to_pi "$PI5_HOST" "$PI5_USER"

    if [ "$setup" = "true" ]; then
        echo -e "${YELLOW}Running setup on Pi 5...${NC}"
        ssh "$PI5_USER@$PI5_HOST" "sudo /opt/jarvis/scripts/setup_pi5.sh"
    fi

    if [ "$restart" = "true" ]; then
        echo -e "${YELLOW}Restarting services on Pi 5...${NC}"
        ssh "$PI5_USER@$PI5_HOST" "sudo systemctl restart jarvis-voice jarvis-sync"
    fi

    echo -e "${GREEN}✓ Pi 5 deployment complete${NC}"
}

deploy_pi4() {
    local setup=$1
    local restart=$2

    echo -e "${YELLOW}Deploying to Pi 4 (Data)...${NC}"

    # Check connectivity
    if ! ping -c 1 "$PI4_HOST" &> /dev/null; then
        echo -e "${RED}Cannot reach $PI4_HOST${NC}"
        exit 1
    fi

    sync_to_pi "$PI4_HOST" "$PI4_USER"

    if [ "$setup" = "true" ]; then
        echo -e "${YELLOW}Running setup on Pi 4...${NC}"
        ssh "$PI4_USER@$PI4_HOST" "sudo /opt/jarvis/scripts/setup_pi4.sh"
    fi

    if [ "$restart" = "true" ]; then
        echo -e "${YELLOW}Restarting services on Pi 4...${NC}"
        ssh "$PI4_USER@$PI4_HOST" "sudo systemctl restart redis-server && cd /opt/homeassistant && docker-compose restart"
    fi

    echo -e "${GREEN}✓ Pi 4 deployment complete${NC}"
}

# Parse arguments
TARGET=""
SETUP=false
RESTART=false

while [[ $# -gt 0 ]]; do
    case $1 in
        pi5|pi4|all|sync)
            TARGET=$1
            shift
            ;;
        --setup)
            SETUP=true
            shift
            ;;
        --restart)
            RESTART=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

if [ -z "$TARGET" ]; then
    usage
    exit 1
fi

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║       JARVIS Deployment Script        ║"
echo "╚═══════════════════════════════════════╝"
echo ""

case $TARGET in
    pi5)
        deploy_pi5 "$SETUP" "$RESTART"
        ;;
    pi4)
        deploy_pi4 "$SETUP" "$RESTART"
        ;;
    all)
        deploy_pi5 "$SETUP" "$RESTART"
        echo ""
        deploy_pi4 "$SETUP" "$RESTART"
        ;;
    sync)
        sync_to_pi "$PI5_HOST" "$PI5_USER"
        sync_to_pi "$PI4_HOST" "$PI4_USER"
        ;;
esac

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
