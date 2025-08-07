#!/bin/bash

# ===============================
# 📄 Script para crear cliente WireGuard
# ===============================

# Nombre del cliente (pasado como argumento)
CLIENT_NAME="$1"

# ===============================
# 📁 Rutas y configuración
# ===============================
WG_DIR="/etc/wireguard"
SERVER_PUBLIC_KEY_PATH="$WG_DIR/server_public.key"
SERVER_IP="3.145.41.118"  # ← Reemplaza por tu IP pública si cambia
CLIENTS_DIR="/home/ubuntu/francho_wire/clientes"
CONF_DIR="$CLIENTS_DIR"
QR_DIR="$CLIENTS_DIR"
WG_PORT="51820"
WG_INTERFACE="wg0"

# ===============================
# 🔎 Verificaciones iniciales
# ===============================
if [ -z "$CLIENT_NAME" ]; then
  echo "❌ Debes indicar un nombre para el cliente."
  echo "➡️  Uso: ./crear_cliente.sh NombreCliente"
  exit 1
fi

if [ ! -f "$SERVER_PUBLIC_KEY_PATH" ]; then
  echo "❌ No se encontró la clave pública del servidor en $SERVER_PUBLIC_KEY_PATH"
  exit 1
fi

mkdir -p "$CLIENTS_DIR"

# ===============================
# 🔐 Generar claves del cliente
# ===============================
CLIENT_PRIVATE_KEY=$(wg genkey)
CLIENT_PUBLIC_KEY=$(echo "$CLIENT_PRIVATE_KEY" | wg pubkey)
CLIENT_IP="10.9.0.$((RANDOM % 200 + 2))/32"

# Leer clave pública del servidor
SERVER_PUBLIC_KEY=$(cat "$SERVER_PUBLIC_KEY_PATH")

# ===============================
# 📝 Crear archivo de configuración del cliente
# ===============================
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

# ===============================
# 🧩 Agregar cliente al servidor (wg0.conf)
# ===============================
echo -e "\n# $CLIENT_NAME" >> "$WG_DIR/$WG_INTERFACE.conf"
echo "[Peer]" >> "$WG_DIR/$WG_INTERFACE.conf"
echo "PublicKey = $CLIENT_PUBLIC_KEY" >> "$WG_DIR/$WG_INTERFACE.conf"
echo "AllowedIPs = ${CLIENT_IP}" >> "$WG_DIR/$WG_INTERFACE.conf"
echo "PersistentKeepalive = 25" >> "$WG_DIR/$WG_INTERFACE.conf"

# 🌀 Aplicar configuración si el servicio está activo
if systemctl is-active --quiet wg-quick@$WG_INTERFACE; then
  echo -e "\n🔁 Aplicando configuración dinámica a la interfaz WireGuard..."
  echo -e "[Peer]\nPublicKey = $CLIENT_PUBLIC_KEY\nAllowedIPs = ${CLIENT_IP}\nPersistentKeepalive = 25" | sudo wg addconf $WG_INTERFACE /dev/stdin
else
  echo "⚠️ La interfaz $WG_INTERFACE no está activa. El cliente fue agregado al archivo pero no aplicado aún."
fi

# ===============================
# 📸 Generar código QR del cliente
# ===============================
qrencode -o "$QR_DIR/$CLIENT_NAME.png" -t png < "$CONFIG_FILE"

# ===============================
# ✅ Finalización
# ===============================
echo "✅ Cliente *$CLIENT_NAME* creado correctamente."
echo "📄 Archivo de configuración: $CONFIG_FILE"
echo "🖼️ QR generado: $QR_DIR/$CLIENT_NAME.png"
