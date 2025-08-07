# config.py

# Token del bot
BOT_TOKEN = '8334285648:AAFui_V95j-RgnTtkYQO_-SdgYCUjX6oBo4'

# ID del administrador autorizado
ADMIN_ID = 1383931339

# Ruta al script bash que crea la config de cada cliente
SCRIPT_PATH = '/home/ubuntu/FranchoWireBot/crear_cliente.sh'

# Carpeta donde el script deja los .conf y los QR
CLIENTS_DIR = '/home/ubuntu/francho_wire/clientes'

# IP pública de tu VPS (para el Endpoint en los archivos .conf)
SERVER_PUBLIC_IP = '3.145.41.118'

# Puerto de WireGuard en el servidor
SERVER_PORT = '51820'

# Rango de IPs internas para asignar dinámicamente a los clientes
IP_RANGO_INICIO = '10.9.0.2'
IP_RANGO_FIN    = '10.9.0.254'

# Planes disponibles y su duración
# Las claves deben coincidir con los botones que muestras en el bot
PLANS = {
    "Free (5 horas)": {"hours": 5},
    "15 días":         {"days": 15},
    "30 días":         {"days": 30},
}
