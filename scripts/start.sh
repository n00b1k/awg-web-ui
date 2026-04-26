#!/bin/sh

mkdir -p /var/log/amnezia
chmod 755 /var/log/amnezia
chmod -R 755 /app/web-ui/

# Проверка nftables
lsmod | grep -E "^nf_tables|^nft_"
nft_true=$?

if [ "$nft_true" -ne 0 ]; then
    ln -sf /sbin/iptables-legacy /sbin/iptables
    echo "iptables-legacy set as default"
fi

# Запуск Flask приложения
exec python3 /app/web-ui/app.py