#!/bin/bash
#
# setup_nginx.sh — host'da nginx + Let's Encrypt TLS o'rnatib, Telegram webhook
# uchun reverse-proxy sozlaydi. Bir nechta loyiha uchun qayta ishlatsa bo'ladi:
# har bir domen + portni alohida chaqirasiz.
#
# Foydalanish:
#   bash setup_nginx.sh <DOMAIN> <PORT> [EMAIL]
#
# Misol:
#   bash setup_nginx.sh smart-tools.uk 8080 siz@email.com
#
# MUHIM: ishga tushirishdan oldin DOMAIN ning DNS A-record'i shu server IP'ga
# ko'rsatib turishi shart (certbot domenni shu orqali tasdiqlaydi).
#
set -euo pipefail

DOMAIN="${1:-}"
PORT="${2:-8080}"
EMAIL="${3:-admin@${DOMAIN}}"

if [ -z "$DOMAIN" ]; then
    echo "❌ Domen ko'rsatilmagan."
    echo "   Foydalanish: bash setup_nginx.sh <DOMAIN> <PORT> [EMAIL]"
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "❌ root sifatida ishga tushiring (yoki: sudo bash setup_nginx.sh ...)."
    exit 1
fi

echo "=== 1/5 nginx + certbot o'rnatish ==="
apt-get update -qq
apt-get install -y nginx certbot python3-certbot-nginx

echo "=== 2/5 nginx server bloki yozish (${DOMAIN} → 127.0.0.1:${PORT}) ==="
# Faqat /webhook/ yo'lini ochamiz — bot main.py da /webhook/<token> da tinglaydi.
# Boshqasini ochmaymiz (xavfsizroq). TLS blokini keyin certbot avtomat qo'shadi.
cat > "/etc/nginx/sites-available/${DOMAIN}" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location /webhook/ {
        proxy_pass         http://127.0.0.1:${PORT};
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"

echo "=== 3/5 nginx konfiguratsiyasini tekshirish ==="
nginx -t
systemctl reload nginx

echo "=== 4/5 Let's Encrypt sertifikat olish (${DOMAIN}) ==="
# --redirect: 80 → 443 avtomat yo'naltiradi. certbot TLS blokini configga qo'shadi.
certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m "${EMAIL}" --redirect
systemctl reload nginx

echo "=== 5/5 Tayyor ==="
echo ""
echo "=================================================="
echo "  nginx + TLS tayyor: https://${DOMAIN}"
echo "  Webhook → 127.0.0.1:${PORT}/webhook/"
echo "  Endi botni ko'taring (python deploy.py)."
echo "=================================================="
