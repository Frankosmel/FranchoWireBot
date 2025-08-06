#!/bin/bash

# ✅ Francho Wire Bot - Script para crear cliente WireGuard
# Guarda configuraciones en: /home/ubuntu/FranchoWireBot/clientes/

# CONFIGURACIÓN DEL SERVIDOR
WG_INTERFACE="wg0"
WG_DIR="/etc/wireguard"
WG_CONF="$WG_DIR/$WG_INTERFACE.conf"
SERVER_PUBLIC_IP="3.145.41.118"
SERVER_PORT="51820"
WG_SUBNET="10.9.0"
WG_CIDR="/32"
DNS_SERVER="1.1.1.1"

# DIRECTORIO DESTINO PARA ARCHIVOS DE CLIENTES
OUTPUT_DIR="/home/ubuntu/FranchoWireBot/clientes"
mkdir -p "$OUTPUT_DIR"

# COMPROBAR PARÁMETRO
CLIENT_NAME="$1"
if [ -z "$CLIENT_NAME" ]; then
  echo "❌ Debes indicar un nombre para el cliente."
  echo "Ejemplo: sudo bash crear_cliente.sh cliente1"
  exit 1
fi

# GENERAR CLAVES DEL CLIENTE
CLIENT_PRIVATE_KEY=$(wg genkey)
CLIENT_PUBLIC_KEY=$(echo "$CLIENT_PRIVATE_KEY" | wg pubkey)

# OBTENER PRÓXIMA IP DISPONIBLE
IP_LAST=$(grep -oP "${WG_SUBNET}\.\K[0-9]{1,3}" "$WG_CONF" | sort -n | tail -n1)
if [ -z "$IP_LAST" ]; then
  IP_LAST=1
fi
NEXT_IP=$((IP_LAST + 1))
CLIENT_IP="$WG_SUBNET.$NEXT_IP$WG_CIDR"

# AGREGAR PEER AL SERVIDOR
echo -e "\n# $CLIENT_NAME" >> "$WG_CONF"
echo "[Peer]" >> "$WG_CONF"
echo "PublicKey = $CLIENT_PUBLIC_KEY" >> "$WG_CONF"
echo "AllowedIPs = $WG_SUBNET.$NEXT_IP$WG_CIDR" >> "$WG_CONF"
echo "PersistentKeepalive = 25" >> "$WG_CONF"

# GENERAR ARCHIVO DEL CLIENTE
CLIENT_CONF="$OUTPUT_DIR/${CLIENT_NAME}.conf"
cat > "$CLIENT_CONF" <<EOF
[Interface]
PrivateKey = $CLIENT_PRIVATE_KEY
Address = $CLIENT_IP
DNS = $DNS_SERVER

[Peer]
PublicKey = $(wg show $WG_INTERFACE public-key)
Endpoint = $SERVER_PUBLIC_IP:$SERVER_PORT
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF

# CAMBIAR PERMISOS DE SEGURIDAD
chmod 600 "$CLIENT_CONF"

# REINICIAR WIREGUARD
systemctl restart wg-quick@$WG_INTERFACE

# GENERAR CÓDIGO QR
qrencode -o "$OUTPUT_DIR/${CLIENT_NAME}.png" < "$CLIENT_CONF"

# MOSTRAR RESULTADO
echo -e "\n✅ Cliente creado: $CLIENT_NAME"
echo "📄 Archivo: $CLIENT_CONF"
echo "📸 QR: $OUTPUT_DIR/${CLIENT_NAME}.png"
