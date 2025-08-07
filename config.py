# config.py

# Token del bot
BOT_TOKEN = '8334285648:AAFui_V95j-RgnTtkYQO_-SdgYCUjX6oBo4'

# ID del administrador autorizado
ADMIN_ID = 1383931339  # Cámbialo si deseas otro ID

# Lista de planes disponibles y sus duraciones
# Las claves deben coincidir con los botones que muestras en el menú
PLANS = {
    "Free (5 horas)": {"hours": 5},
    "15 días":        {"days": 15},
    "30 días":        {"days": 30},
}

# Ruta al script bash que crea el cliente WireGuard
SCRIPT_PATH = '/home/ubuntu/FranchoWireBot/crear_cliente.sh'

# Directorio donde se almacenan las configuraciones y QR generados (.conf + .png)
CLIENTS_DIR = '/home/ubuntu/francho_wire/clientes'

# IP pública del servidor (para el campo Endpoint de los .conf)
SERVER_PUBLIC_IP = '3.145.41.118'

# Parámetros de WireGuard (usados en utils.py / generator.py)
WG_INTERFACE      = 'wg0'
WG_PORT           = 51820
WG_CONFIG_DIR     = '/etc/wireguard/configs'
WG_NETWORK_RANGE  = '0.0.0.0/0'
