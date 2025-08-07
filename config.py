config.py

Token del bot (reemplázalo con tu token real)

BOT_TOKEN = '8334285648:AAFui_V95j-RgnTtkYQO_-SdgYCUjX6oBo4'

ID del administrador autorizado (solo este accede al bot)

ADMIN_ID = 1383931339  # Reemplaza por tu ID si cambia

Ruta correcta al script bash para crear clientes

SCRIPT_PATH = '/home/ubuntu/FranchoWireBot/crear_cliente.sh'

Carpeta donde se guardan los archivos generados por el script

CLIENTS_DIR = '/home/ubuntu/francho_wire/clientes'

Clave pública del servidor WireGuard (para crear .conf)

SERVER_PUBLIC_KEY = 'QLtoHUIcW2s/ZZ3tgKZ3wSidEy778prOGWIGo2cXhHw='

IP pública del servidor WireGuard (Endpoint)

SERVER_PUBLIC_IP = '3.145.41.118'

Puerto de escucha del servidor WireGuard (por defecto 51820)

LISTEN_PORT = 51820 WG_PORT = LISTEN_PORT

Rango permitido de IPs para clientes (AllowedIPs)

WG_NETWORK_RANGE = '0.0.0.0/0'

Carpeta donde se mantienen las configuraciones activas del servidor

WG_CONFIG_DIR = '/etc/wireguard/configs'

Endpoint completo para el .conf de cliente

SERVER_ENDPOINT = f'{SERVER_PUBLIC_IP}:{WG_PORT}'

Planes disponibles y su duración (para menús y cálculos de vencimiento)

PLANS = { 'Free (5 horas)': {'horas': 5}, '15 días': {'dias': 15}, '30 días': {'dias': 30} }

