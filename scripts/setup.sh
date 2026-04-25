#!/usr/bin/env bash
# setup.sh — Install dependencies on Ubuntu 24 droplet
set -euo pipefail

echo "=== LPII AutoGrader — Setup ==="

# System packages
echo "[1/5] Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    gcc g++ valgrind git \
    nginx certbot python3-certbot-nginx \
    sqlite3 curl

# Application directory
APP_DIR="/opt/lpii-autograder"
echo "[2/5] Setting up application directory..."
mkdir -p "$APP_DIR"
mkdir -p "$APP_DIR/storage/db"
mkdir -p "$APP_DIR/storage/submissions"
mkdir -p "$APP_DIR/storage/assignments"

# Python virtual environment
echo "[3/5] Creating Python virtual environment..."
python3 -m venv "$APP_DIR/venv"
source "$APP_DIR/venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$APP_DIR/requirements.txt"

# Application user
echo "[4/5] Creating application user..."
id -u autograder &>/dev/null || useradd --system --home "$APP_DIR" --shell /bin/false autograder
chown -R autograder:autograder "$APP_DIR/storage"

# Systemd services
echo "[5/5] Installing systemd services..."

cat > /etc/systemd/system/autograder.service << 'EOF'
[Unit]
Description=LPII AutoGrader Web
After=network.target

[Service]
Type=exec
User=autograder
Group=autograder
WorkingDirectory=/opt/lpii-autograder
Environment=PATH=/opt/lpii-autograder/venv/bin:/usr/bin:/bin
Environment=STORAGE_DIR=/opt/lpii-autograder/storage
ExecStart=/opt/lpii-autograder/venv/bin/gunicorn main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/autograder/access.log \
    --error-logfile /var/log/autograder/error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/autograder-worker.service << 'EOF'
[Unit]
Description=LPII AutoGrader Grading Worker
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=/opt/lpii-autograder
Environment=PATH=/opt/lpii-autograder/venv/bin:/usr/bin:/bin
Environment=STORAGE_DIR=/opt/lpii-autograder/storage
ExecStart=/opt/lpii-autograder/venv/bin/python grader/worker.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

mkdir -p /var/log/autograder
chown autograder:autograder /var/log/autograder

systemctl daemon-reload
systemctl enable autograder autograder-worker

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Copy application code to $APP_DIR"
echo "  2. Set SECRET_KEY: export SECRET_KEY=\$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
echo "  3. Create admin: python3 scripts/create_admin.py --name 'Prof Bidu' --email bidu@lavid.ufpb.br --password <senha>"
echo "  4. Run deploy.sh to configure Nginx and start services"
