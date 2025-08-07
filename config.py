# config.py

# — Bot —
BOT_TOKEN = '8334285648:AAFui_V95j-RgnTtkYQO_-SdgYCUjX6oBo4'
ADMIN_ID   = 1383931339  # Tu ID de Telegram

# — Rutas —
SCRIPT_PATH    = '/home/ubuntu/FranchoWireBot/crear_cliente.sh'    # ruta al script bash
CLIENTS_DIR    = '/home/ubuntu/francho_wire/clientes'             # donde se guardan .conf y .png
CLIENTES_DIR   = CLIENTS_DIR                                      # alias español (para import en admin_handlers)

# — WireGuard servidor —
WG_INTERFACE        = 'wg0'
WG_CONFIG_DIR       = f'/etc/wireguard/configs'                   # donde guarda wg-quick sus .conf
WG_PORT             = 51820
IP_RANGO_INICIO = '10.9.0.2'
SERVER_PUBLIC_IP    = '3.145.41.118'
SERVER_PUBLIC_KEY   = '/etc/wireguard/server_public.key'          # ruta a tu clave pública
SERVER_ENDPOINT     = f'{SERVER_PUBLIC_IP}:{WG_PORT}'
WG_NETWORK_RANGE    = '0.0.0.0/0'

# — Planes de cliente —
PLANES_PRECIOS = {
    "Free (5 horas)": {"horas": 5},
    "15 días":        {"dias": 15},
    "30 días":        {"dias": 30},
}
PLANES = list(PLANES_PRECIOS.keys())
PLANS  = PLANES  # alias para quienes importen PLANS

# — Logs y demás (opcional) —
GRUPO_LOGS = None
