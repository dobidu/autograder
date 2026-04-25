#!/usr/bin/env bash
# deploy.sh — Deploy/update the application
set -euo pipefail

APP_DIR="/opt/lpii-autograder"
DOMAIN="${1:-}"

echo "=== LPII AutoGrader — Deploy ==="

# Sync code
echo "[1/4] Syncing application code..."
rsync -a --exclude='storage' --exclude='venv' --exclude='__pycache__' \
    --exclude='.git' --exclude='*.pyc' --exclude='.DS_Store' \
    . "$APP_DIR/"

# Install/update dependencies
echo "[2/4] Updating dependencies..."
source "$APP_DIR/venv/bin/activate"
pip install --quiet -r "$APP_DIR/requirements.txt"

# Nginx configuration
if [ -n "$DOMAIN" ]; then
    echo "[3/4] Configuring Nginx for $DOMAIN..."
    cat > /etc/nginx/sites-available/autograder << NGINX
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 15M;

    location /static/ {
        alias $APP_DIR/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
NGINX
    ln -sf /etc/nginx/sites-available/autograder /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
    echo "    Nginx configured. Run 'certbot --nginx -d $DOMAIN' for HTTPS."
else
    echo "[3/4] Skipping Nginx (no domain provided). Usage: deploy.sh yourdomain.com"
fi

# Restart services
echo "[4/4] Restarting services..."
systemctl restart autograder
systemctl restart autograder-worker

echo ""
echo "=== Deploy complete ==="
systemctl status autograder --no-pager -l || true
echo ""
systemctl status autograder-worker --no-pager -l || true
