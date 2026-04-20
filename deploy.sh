#!/bin/bash
set -e

source ~/Dev/devtools/lib/vps_config.sh
REMOTE_DIR="/var/www/assets"
DOMAIN="assets.tianlizeng.cloud"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "→ Generating site..."
/opt/homebrew/bin/python3 generate.py

echo "→ Syncing to VPS..."
ssh "$VPS" "mkdir -p $REMOTE_DIR"
rsync -avz --delete site/ "$VPS:$REMOTE_DIR/"

echo "→ Reloading nginx (no-op if config unchanged)..."
ssh "$VPS" "nginx -t && systemctl reload nginx" >/dev/null

echo "→ Verifying..."
sleep 1
HTTP_CODE=$(curl --noproxy '*' -s -o /dev/null -w "%{http_code}" "https://$DOMAIN" || echo "000")
case "$HTTP_CODE" in
  200) echo "✓ Deployed: https://$DOMAIN (HTTP 200)" ;;
  302) echo "✓ Deployed: https://$DOMAIN (CF redirect — 应该是 public 状态，检查 Origin Rule)" ;;
  000) echo "✗ DNS/network error — check CF DNS and Origin Rule" ;;
  *)   echo "⚠ HTTP $HTTP_CODE — 检查 Nginx config" ;;
esac
