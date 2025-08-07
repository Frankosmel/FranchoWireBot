# config.py

# Token del bot
BOT_TOKEN = '8334285648:AAFui_V95j-RgnTtkYQO_-SdgYCUjX6oBo4'

# ID del administrador autorizado
ADMIN_ID = 1383931339  # Cámbialo si deseas otro ID

# Ruta correcta al script bash para crear clientes
SCRIPT_PATH = '/home/ubuntu/FranchoWireBot/crear_cliente.sh'  # ✅ Corregido

# Carpeta donde se guardan los archivos generados por el script
CLIENTS_DIR = '/home/ubuntu/francho_wire/clientes'

# IP pública del servidor
SERVER_PUBLIC_IP = '3.145.41.118' 

# Puerto donde escucha el servidor WireGuard
LISTEN_PORT = 51820

# Ruta base donde se almacenan los .conf
WG_CONFIG_DIR = '/etc/wireguard'

# Planes disponibles
PLANS = {
    "🧪 Prueba gratuita (5h)": 5,
    "📅 Plan Diario (24h)": 24,
    "🗓 Plan Semanal (7 días)": 24 * 7,
    "📆 Plan Mensual (30 días)": 24 * 30,
}

# Configuraciones para recordatorios antes de vencer
AVISOS_VENCIMIENTO_HORAS = [72, 24]  # 3 días y 1 día antes

# Cada cuánto se revisan las expiraciones (en segundos)
REVISIÓN_INTERVALO_SEGUNDOS = 3600  # 1 hora
