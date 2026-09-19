#!/bin/bash
#
# Garden Bot - Setup script for Raspberry Pi
# Assumes repo has already been cloned: git clone https://github.com/JamieDF/garden-bot.git
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_DIR="$PROJECT_DIR/pi"

echo "🌱 Garden Bot - Setup"
echo "================================"
echo ""

# Check if running as pi user
if [ "$USER" != "pi" ]; then
    echo "⚠️  Warning: This script is designed to run as the 'pi' user."
    echo "   Current user: $USER"
    echo ""
fi

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "========================================="
echo "Step 1: OS packages"
echo "========================================="
sudo apt update
sudo apt install -y \
    python3-full \
    python3-pip \
    python3-venv \
    python3-dev \
    libffi-dev \
    libssl-dev \
    i2c-tools \
    libopenblas-dev \
    liblapack-dev \
    libcamera-apps \
    libcamera-tools \
    git \
    nodejs \
    npm
echo ""

echo "========================================="
echo "Step 2: Enable interfaces"
echo "========================================="
echo "   Enabling I2C..."
sudo raspi-config nonint do_i2c 0
echo "   Enabling 1-Wire..."
sudo raspi-config nonint do_onewire 0
echo "   Enabling camera..."
sudo raspi-config nonint do_camera 0
echo "   Enabling SSH..."
sudo raspi-config nonint do_ssh 0
echo ""

echo "========================================="
echo "Step 3: Load kernel modules"
echo "========================================="
sudo modprobe i2c-bcm2835
sudo modprobe w1-gpio

echo "i2c-bcm2835" | sudo tee /etc/modules-load.d/i2c.conf > /dev/null
echo "w1-gpio" | sudo tee /etc/modules-load.d/w1-gpio.conf > /dev/null
echo ""

echo "========================================="
echo "Step 4: Verify sensors (optional)"
echo "========================================="
if command -v i2cdetect &> /dev/null; then
    echo "   I2C bus 1:"
    i2cdetect -y 1 2>/dev/null || echo "   (no devices yet)"
fi
if [ -d /sys/bus/w1/devices ]; then
    echo "   1-Wire devices:"
    ls /sys/bus/w1/devices/ 2>/dev/null | grep "^28-" || echo "   (no devices yet)"
fi
echo ""

echo "========================================="
echo "Step 5: Python virtual environment"
echo "========================================="
cd "$PROJECT_DIR"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r "$APP_DIR/requirements.txt"
echo ""

echo "========================================="
echo "Step 6: Frontend build"
echo "========================================="
if [ ! -d "$PROJECT_DIR/frontend/node_modules" ]; then
    cd "$PROJECT_DIR/frontend"
    npm install
fi
cd "$PROJECT_DIR/frontend"
npm run build
echo ""

echo "========================================="
echo "Step 7: Data directory"
echo "========================================="
sudo mkdir -p /var/lib/garden-bot
sudo chown pi:pi /var/lib/garden-bot
echo ""

echo "========================================="
echo "Step 8: Environment file"
echo "========================================="
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "   Created .env — edit it if needed"
else
    echo "   .env already exists"
fi
echo ""

echo "========================================="
echo "Step 9: Systemd services"
echo "========================================="
sudo cp "$APP_DIR/services/sensor-poller.service" /etc/systemd/system/
sudo cp "$APP_DIR/services/garden-api.service" /etc/systemd/system/
sudo cp "$APP_DIR/services/garden-agent.service" /etc/systemd/system/
sudo systemctl daemon-reload
echo ""

echo "========================================="
echo "Step 10: Starting services"
echo "========================================="
sudo systemctl enable --now sensor-poller
sudo systemctl enable --now garden-api
sudo systemctl enable --now garden-agent
echo ""

echo "========================================="
echo "✅ Setup complete!"
echo "========================================="
echo ""
echo "Services:"
echo "  sensor-poller  $(systemctl is-active sensor-poller 2>/dev/null || echo 'inactive')"
echo "  garden-api     $(systemctl is-active garden-api 2>/dev/null || echo 'inactive')"
echo "  garden-agent   $(systemctl is-active garden-agent 2>/dev/null || echo 'inactive')"
echo ""
echo "View logs:"
echo "  journalctl -u sensor-poller -f"
echo "  journalctl -u garden-api -f"
echo ""
echo "API:  http://$(hostname -I | awk '{print $1}'):8000"
echo "Docs: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
