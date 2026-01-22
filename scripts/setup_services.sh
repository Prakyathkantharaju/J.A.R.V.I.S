#!/bin/bash
# Setup JARVIS systemd services on Raspberry Pi
# Run this script on the Pi: bash ~/life_os/scripts/setup_services.sh

set -e

echo "=== Setting up JARVIS systemd services ==="

# Copy service files
sudo cp ~/life_os/deploy/systemd/jarvis-api.service /etc/systemd/system/
sudo cp ~/life_os/deploy/systemd/jarvis-sync.service /etc/systemd/system/
sudo cp ~/life_os/deploy/systemd/whoop-refresh.service /etc/systemd/system/
sudo cp ~/life_os/deploy/systemd/whoop-refresh.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable jarvis-api.service
sudo systemctl enable jarvis-sync.service
sudo systemctl enable whoop-refresh.timer

# Start services
sudo systemctl start jarvis-api.service
echo "Started jarvis-api.service"

# Start Whoop token refresh timer
sudo systemctl start whoop-refresh.timer
echo "Started whoop-refresh.timer (refreshes tokens every 30 min)"

echo ""
echo "=== Services installed ==="
echo ""
echo "Commands:"
echo "  sudo systemctl status jarvis-api       # Check API server status"
echo "  sudo systemctl restart jarvis-api      # Restart API server"
echo "  sudo journalctl -u jarvis-api -f       # View logs"
echo "  sudo systemctl list-timers             # View active timers"
echo "  sudo journalctl -u whoop-refresh       # View token refresh logs"
echo ""
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):8000"
echo ""
