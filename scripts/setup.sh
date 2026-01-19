#!/bin/bash
# JARVIS - Main Setup Script
# Run this after cloning to set up the development environment

set -e

echo "🤖 Setting up JARVIS..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for required tools
check_requirements() {
    echo -e "${YELLOW}Checking requirements...${NC}"

    # Check for uv
    if ! command -v uv &> /dev/null; then
        echo -e "${YELLOW}Installing uv...${NC}"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    echo -e "${GREEN}✓ uv installed${NC}"

    # Check for Python 3.12+
    if ! uv python list | grep -q "3.12"; then
        echo -e "${YELLOW}Installing Python 3.12...${NC}"
        uv python install 3.12
    fi
    echo -e "${GREEN}✓ Python 3.12 available${NC}"

    # Check for Node.js (for Clawdbot)
    if ! command -v node &> /dev/null; then
        echo -e "${YELLOW}Node.js not found. Install it for Clawdbot integration.${NC}"
        echo "  brew install node  # macOS"
        echo "  sudo apt install nodejs  # Ubuntu/Debian"
    else
        echo -e "${GREEN}✓ Node.js installed${NC}"
    fi
}

# Set up Python environment
setup_python() {
    echo -e "${YELLOW}Setting up Python environment...${NC}"

    # Sync dependencies
    uv sync

    echo -e "${GREEN}✓ Python dependencies installed${NC}"
}

# Set up configuration
setup_config() {
    echo -e "${YELLOW}Setting up configuration...${NC}"

    # Create config directory
    mkdir -p ~/.config/jarvis
    mkdir -p ~/.local/share/jarvis
    mkdir -p ~/.local/state/jarvis

    # Copy .env if it doesn't exist
    if [ ! -f .env ]; then
        cp .env.example .env
        echo -e "${YELLOW}Created .env file. Please edit it with your credentials.${NC}"
    else
        echo -e "${GREEN}✓ .env already exists${NC}"
    fi
}

# Set up Clawdbot (optional)
setup_clawdbot() {
    echo -e "${YELLOW}Setting up Clawdbot (optional)...${NC}"

    if command -v npm &> /dev/null; then
        read -p "Install Clawdbot? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            npm install -g clawdbot@latest
            echo -e "${GREEN}✓ Clawdbot installed${NC}"
            echo -e "${YELLOW}Run 'clawdbot onboard' to complete setup${NC}"
        fi
    else
        echo -e "${YELLOW}Skipping Clawdbot (npm not available)${NC}"
    fi
}

# Main setup flow
main() {
    echo ""
    echo "╔═══════════════════════════════════════╗"
    echo "║         JARVIS Setup Script           ║"
    echo "╚═══════════════════════════════════════╝"
    echo ""

    check_requirements
    setup_python
    setup_config
    setup_clawdbot

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo -e "${GREEN}  JARVIS setup complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Edit .env with your API credentials"
    echo "  2. Run: uv run python scripts/oauth_setup.py"
    echo "  3. Test: uv run jarvis --help"
    echo ""
}

main "$@"
