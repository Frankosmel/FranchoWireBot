# config.py

# 🎯 Token del bot de Telegram
BOT_TOKEN = '8334285648:AAFui_V95j-RgnTtkYQO_-SdgYCUjX6oBo4'

# 👨‍💻 ID del administrador (solo esta persona podrá usar el bot)
ADMIN_ID = 1383931339  # Cambia este ID si deseas autorizar a otro usuario

# 📁 Ruta al script bash que crea clientes y genera configuraciones
SCRIPT_PATH = '/home/ubuntu/FranchoWireBot/crear_cliente.sh'

# 📂 Carpeta donde se guardan las configuraciones generadas (.conf y QR)
CLIENTS_DIR = '/home/ubuntu/francho_wire/clientes'

# 🌐 IP pública del servidor (se usará en las configuraciones .conf)
SERVER_PUBLIC_IP = '3.145.41.118'

# 📦 Planes disponibles para los clientes (nombre, precio y duración)
PLANS = {
    "🆓 Prueba (5h)": {
        "precio": 0,
        "duración_horas": 5
    },
    "💵 Plan Básico (7 días)": {
        "precio": 100,
        "duración_dias": 7
    },
    "💎 Plan Premium (30 días)": {
        "precio": 300,
        "duración_dias": 30
    }
}
