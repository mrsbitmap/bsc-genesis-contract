#!/bin/bash
# ==============================================================================
# OCI AI Node Auto-Installer for Video & Audio Pipeline
# Optimized for Oracle Cloud GPU Instances (e.g., VM.GPU.A10.1 / NVIDIA A10/A100)
# Run as root / sudo: sudo bash install_oci_ai.sh
# ==============================================================================

set -euo pipefail

LOGFILE="/var/log/oci_ai_install.log"
exec > >(tee -a "$LOGFILE") 2>&1

echo "=== [1/6] System Update & Essential Package Installation ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y \
    build-essential \
    curl \
    wget \
    git \
    ffmpeg \
    jq \
    rsync \
    screen \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ca-certificates \
    gnupg \
    lsb-release

echo "=== [2/6] Checking NVIDIA Drivers & CUDA Setup ==="
REBOOT_REQUIRED=0
if ! command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA Driver not detected. Installing standard server drivers (nvidia-driver-550-server)..."
    apt-get install -y nvidia-driver-550-server || apt-get install -y nvidia-driver-535-server
    REBOOT_REQUIRED=1
else
    echo "NVIDIA Driver detected successfully:"
    nvidia-smi
fi

echo "=== [3/6] Installing Docker & NVIDIA Container Toolkit ==="
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm -f get-docker.sh
fi

NON_ROOT_USER=${SUDO_USER:-ubuntu}
if id "$NON_ROOT_USER" &>/dev/null; then
    usermod -aG docker "$NON_ROOT_USER" || true
fi

# Setup NVIDIA Container Toolkit if nvidia-smi is available
if command -v nvidia-smi &> /dev/null; then
    echo "Setting up NVIDIA Container Toolkit..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

    apt-get update -y
    apt-get install -y nvidia-container-toolkit
    nvidia-ctk runtime configure --runtime=docker || true
    systemctl restart docker || true
fi

echo "=== [4/6] Setting Up Workspace Directory ==="
WORK_DIR="/opt/ai-studio"
mkdir -p "$WORK_DIR/inputs"
mkdir -p "$WORK_DIR/outputs"
mkdir -p "$WORK_DIR/models/diffusion_models"
mkdir -p "$WORK_DIR/models/clip"
mkdir -p "$WORK_DIR/models/vae"
mkdir -p "$WORK_DIR/scripts"

chown -R "$NON_ROOT_USER:$NON_ROOT_USER" "$WORK_DIR"
chmod -R 755 "$WORK_DIR"

echo "=== [5/6] Setting Up ComfyUI & AI Pipeline Environment ==="
if [ ! -d "$WORK_DIR/ComfyUI" ]; then
    echo "Cloning ComfyUI..."
    su - "$NON_ROOT_USER" -c "git clone https://github.com/comfyanonymous/ComfyUI.git $WORK_DIR/ComfyUI"
fi

# Set up Python virtual environment for ComfyUI & AI Pipeline
ENV_DIR="$WORK_DIR/venv"
if [ ! -d "$ENV_DIR" ]; then
    echo "Creating Python virtualenv at $ENV_DIR..."
    su - "$NON_ROOT_USER" -c "python3 -m venv $ENV_DIR"
fi

su - "$NON_ROOT_USER" -c "source $ENV_DIR/bin/activate && pip install --upgrade pip setuptools wheel"
su - "$NON_ROOT_USER" -c "source $ENV_DIR/bin/activate && pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121" || true
su - "$NON_ROOT_USER" -c "source $ENV_DIR/bin/activate && cd $WORK_DIR/ComfyUI && pip install -r requirements.txt"
su - "$NON_ROOT_USER" -c "source $ENV_DIR/bin/activate && pip install requests websocket-client pydantic edge-tts f5-tts" || true

# Clone ComfyUI Custom Nodes (Manager & Video Helper Suite)
MANAGER_DIR="$WORK_DIR/ComfyUI/custom_nodes/ComfyUI-Manager"
if [ ! -d "$MANAGER_DIR" ]; then
    echo "Installing ComfyUI-Manager..."
    su - "$NON_ROOT_USER" -c "git clone https://github.com/ltdrdata/ComfyUI-Manager.git $MANAGER_DIR"
fi

VHS_DIR="$WORK_DIR/ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite"
if [ ! -d "$VHS_DIR" ]; then
    echo "Installing ComfyUI-VideoHelperSuite..."
    su - "$NON_ROOT_USER" -c "git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite $VHS_DIR"
    su - "$NON_ROOT_USER" -c "source $ENV_DIR/bin/activate && cd $VHS_DIR && pip install -r requirements.txt" || true
fi

echo "=== [6/6] Installation Complete ==="
echo "Workspace created at: $WORK_DIR"
echo "Inputs:  $WORK_DIR/inputs"
echo "Outputs: $WORK_DIR/outputs"

if [ "$REBOOT_REQUIRED" -eq 1 ]; then
    echo "----------------------------------------------------------------------"
    echo "ATTENTION: NVIDIA driver was installed. Please reboot the instance now!"
    echo "Command: sudo reboot"
    echo "----------------------------------------------------------------------"
fi
