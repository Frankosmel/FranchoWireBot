# crear_cliente.sh

#!/bin/bash

# ===============================
# 📄 Script para crear cliente WireGuard
# ===============================

# Nombre del cliente (pasado como argumento)
CLIENT_NAME="$1"

# Rutas
WG_DIR="/etc/wireguard"
SERVER_PUBLIC_KEY_PATH="$WG_DIR/server_public.key"  # ← Corregido
SERVER_IP="3.145.41.118"  # Reemplaza esto con tu IP pública
CLIENTS_DIR="/home/ubuntu/francho_wire/clientes"
CONF_DIR="$CLIENTS_DIR"
QR_DIR="$CLIENTS_DIR"
WG_PORT="51820"
WG_INTERFACE="wg0"

# Verificaciones iniciales
if [ -z "$CLIENT_NAME" ]; then
  echo "❌ Debes indicar un nombre para el cliente."
  exit 1
fi

if [ ! -f "$SERVER_PUBLIC_KEY_PATH" ]; then
  echo "❌ No se encontró la clave pública del servidor en $SERVER_PUBLIC_KEY_PATH"
  exit 1
fi

mkdir -p "$CLIENTS_DIR"

# Generar claves del cliente
CLIENT_PRIVATE_KEY=$(wg genkey)
CLIENT_PUBLIC_KEY=$(echo "$CLIENT_PRIVATE_KEY" | wg pubkey)
CLIENT_IP="10.9.0.$((RANDOM % 200 + 2))/32"

# Leer clave pública del servidor
SERVER_PUBLIC_KEY=$(cat "$SERVER_PUBLIC_KEY_PATH")

# Crear archivo de configuración
CONFIG_FILE="$CONF_DIR/$CLIENT_NAME.conf"
cat > "$CONFIG_FILE" <<EOF
[Interface]
PrivateKey = $CLIENT_PRIVATE_KEY
Address = $CLIENT_IP
DNS = 1.1.1.1

[Peer]
PublicKey = $SERVER_PUBLIC_KEY
Endpoint = $SERVER_IP:$WG_PORT
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF

# Generar QR
qrencode -o "$QR_DIR/$CLIENT_NAME.png" -t png < "$CONFIG_FILE"

echo "✅ Cliente $CLIENT_NAME creado correctamente."
echo "📄 Archivo: $CONFIG_FILE"
echo "🖼️ QR: $QR_DIR/$CLIENT_NAME.png"
