#!/bin/bash
# ==============================================================================
# Security & System Setup Script for OCI AI Pipeline
# Sets up safe iptables firewall rules, directory structures, and systemd services.
# Run as root / sudo: sudo bash setup_secure_pipeline.sh
# ==============================================================================

set -euo pipefail

echo "=== [1/4] Configuring Firewall (iptables / ufw) ==="

if command -v ufw &>/dev/null && ufw status | grep -q "active"; then
    echo "UFW active. Allowing SSH port 22..."
    ufw allow 22/tcp
else
    echo "Configuring iptables rules..."
    iptables -A INPUT -i lo -j ACCEPT
    iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
    iptables -A INPUT -p tcp --dport 22 -j ACCEPT
    iptables -A INPUT -i docker0 -j ACCEPT
fi

echo "=== [2/4] Verifying Directory Permissions ==="
WORK_DIR="/opt/ai-studio"
NON_ROOT_USER=${SUDO_USER:-ubuntu}

mkdir -p "$WORK_DIR/inputs"
mkdir -p "$WORK_DIR/outputs"
mkdir -p "$WORK_DIR/models"
mkdir -p "$WORK_DIR/scripts"

if id "$NON_ROOT_USER" &>/dev/null; then
    chown -R "$NON_ROOT_USER:$NON_ROOT_USER" "$WORK_DIR"
fi
chmod -R 750 "$WORK_DIR"

echo "=== [3/4] Creating Systemd Service for ComfyUI Backend ==="
COMFY_SERVICE_FILE="/etc/systemd/system/comfyui.service"

cat << EOF > "$COMFY_SERVICE_FILE"
[Unit]
Description=ComfyUI AI Server Backend
After=network.target

[Service]
Type=simple
User=$NON_ROOT_USER
WorkingDirectory=$WORK_DIR/ComfyUI
ExecStart=$WORK_DIR/venv/bin/python3 main.py --listen 127.0.0.1 --port 8188
Restart=always
RestartSec=5
Environment="PATH=$WORK_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
EOF

echo "=== [4/4] Creating Systemd Service for Background Worker ==="
WORKER_SERVICE_FILE="/etc/systemd/system/ai-worker.service"

cat << EOF > "$WORKER_SERVICE_FILE"
[Unit]
Description=OCI AI Production Worker Daemon
After=network.target comfyui.service
Wants=comfyui.service

[Service]
Type=simple
User=$NON_ROOT_USER
WorkingDirectory=$WORK_DIR
ExecStart=$WORK_DIR/venv/bin/python3 $WORK_DIR/scripts/worker.py
Restart=on-failure
RestartSec=10
Environment="PATH=$WORK_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "Systemd services created:"
echo " - ComfyUI:   /etc/systemd/system/comfyui.service"
echo " - AI Worker: /etc/systemd/system/ai-worker.service"
echo ""
echo "You can start services with:"
echo "  sudo systemctl start comfyui ai-worker"
echo "  sudo systemctl enable comfyui ai-worker"
echo ""
echo "=== Setup completed successfully! ==="
