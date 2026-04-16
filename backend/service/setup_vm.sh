#!/bin/bash
# Google Cloud VM Setup Script
# Run this on your VM after first SSH

set -e  # Exit on error

echo "========================================="
echo "Deepfake Detector - VM Setup"
echo "========================================="
echo ""

# Update system
echo "[INFO] Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo "[INFO] Installing system dependencies..."
sudo apt install -y \
    ffmpeg \
    git \
    python3-pip \
    python3-venv \
    wget \
    curl \
    htop \
    screen \
    build-essential

# Verify ffmpeg
echo "[INFO] Verifying ffmpeg installation..."
ffmpeg -version | head -n 1

# Upgrade pip
echo "[INFO] Upgrading pip..."
pip3 install --upgrade pip

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "[WARNING] Warning: requirements.txt not found in current directory"
    echo "Make sure you're in the backend folder of your project"
    echo "Example: cd ~/credibility_checker/backend"
    exit 1
fi

# Install Python dependencies
echo "[INFO] Installing Python dependencies..."
pip3 install -r requirements.txt

# Verify installations
echo "[INFO] Verifying Python packages..."
python3 -c "import fastapi; print('[SUCCESS] FastAPI installed')"
python3 -c "import uvicorn; print('[SUCCESS] Uvicorn installed')"

# Check if NVIDIA drivers needed (GPU instance)
if lspci | grep -i nvidia > /dev/null; then
    echo "[INFO] NVIDIA GPU detected!"
    
    # Check if drivers already installed
    if ! command -v nvidia-smi &> /dev/null; then
        echo "[INFO] Installing NVIDIA drivers..."
        sudo apt install -y ubuntu-drivers-common
        sudo ubuntu-drivers autoinstall
        echo "[WARNING] GPU drivers installed. Please reboot the VM:"
        echo "    sudo reboot"
        echo "Then re-run this script and SSH back in."
        exit 0
    else
        echo "[SUCCESS] NVIDIA drivers already installed"
        nvidia-smi
    fi
else
    echo "[INFO] No NVIDIA GPU detected (this is fine for CPU-only instances)"
fi

# Create logs directory
mkdir -p logs

# Test the server
echo ""
echo "========================================="
echo "[SUCCESS] Setup complete!"
echo "========================================="
echo ""
echo "To run the server:"
echo "  python3 fastapi_server.py"
echo ""
echo "Or to run in background:"
echo "  nohup python3 fastapi_server.py > logs/server.log 2>&1 &"
echo ""
echo "To test the endpoint:"
echo "  curl http://localhost:8000/"
echo ""

# Ask if user wants to create systemd service
read -p "Would you like to create a systemd service for auto-start? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    USERNAME=$(whoami)
    WORKDIR=$(pwd)
    
    sudo tee /etc/systemd/system/deepfake-api.service > /dev/null <<EOF
[Unit]
Description=Deepfake Detector FastAPI
After=network.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$WORKDIR
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 -m uvicorn fastapi_server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable deepfake-api
    
    echo ""
    echo "[SUCCESS] Systemd service created!"
    echo ""
    echo "To control the service:"
    echo "  sudo systemctl start deepfake-api    # Start"
    echo "  sudo systemctl stop deepfake-api     # Stop"
    echo "  sudo systemctl restart deepfake-api  # Restart"
    echo "  sudo systemctl status deepfake-api   # Check status"
    echo "  sudo journalctl -u deepfake-api -f   # View logs"
    echo ""
    
    read -p "Start the service now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl start deepfake-api
        sleep 2
        sudo systemctl status deepfake-api
        echo ""
        echo "Testing endpoint..."
        sleep 2
        curl http://localhost:8000/
        echo ""
        echo ""
        echo "[SUCCESS] Service is running!"
    fi
fi

echo ""
echo "========================================="
echo "Next Steps:"
echo "========================================="
echo "1. Get your VM's public IP:"
echo "   On your local computer, run:"
echo "   gcloud compute instances describe deepfake-detector --zone=europe-west2-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'"
echo ""
echo "2. Update your Chrome extension:"
echo "   - Edit extension/background.js"
echo "   - Change API_ENDPOINT to your VM's IP"
echo "   - Reload the extension"
echo ""
echo "3. Test from your browser!"
echo ""
