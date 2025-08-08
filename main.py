# main.py

import os
import threading
import time
from datetime import datetime
from telebot import TeleBot

from config import (
    BOT_TOKEN,
    ADMIN_ID,
    SCRIPT_PATH,
    CLIENTS_DIR
)
from storage import load_json  # para leer configuraciones
from admin_handlers import register_admin_handlers  # tus handlers de admin
from payments_handlers import register_payments_handlers  # ⬅️ agrega /planes y flujo de pagos

# Ruta al JSON donde guardas tus metadatos de clientes
CONFIGS_FILE = os.path.join(CLIENTS_DIR, "configuraciones.json")
# Umbral en horas para disparar la notificación antes de expirar
ALERT_THRESHOLD_HOURS = 1.0

bot = TeleBot(BOT_TOKEN)

def is_admin(user_id):
    return user_id == ADMIN_ID

def expiration_watcher():
    """
    Hilo en segundo plano que cada hora revisa todas las configuraciones
    y alerta al ADMIN si alguna vence en las próximas ALERT_THRESHOLD_HOURS.
    """
    notified = set()
    while True:
        try:
            if os.path.exists(CONFIGS_FILE):
                data = load_json(CONFIGS_FILE)
            else:
                data = {}
            now = datetime.now()
            for client, info in data.items():
                venc_str = info.get('vencimiento')
                if not venc_str:
                    continue
                # Ajusta el formato según cómo lo guardas en tu JSON
                venc = datetime.strptime(venc_str, "%Y-%m-%d %H:%M")
                hours_left = (venc - now).total_seconds() / 3600
                key = (client, venc_str)
                if 0 < hours_left <= ALERT_THRESHOLD_HOURS and key not in notified:
                    bot.send_message(
                        ADMIN_ID,
                        f"⚠️ La configuración *{client}* vencerá en aproximadamente "
                        f"*{hours_left:.1f}* horas (vence {venc.strftime('%d/%m/%Y %I:%M %p')}).",
                        parse_mode="Markdown"
                    )
                    notified.add(key)
        except Exception as e:
            # En caso de error lo mostramos por consola y seguimos
            print(f"[expiration_watcher] error: {e}")
        # Espera una hora antes de la próxima comprobación
        time.sleep(3600)

if __name__ == '__main__':
    # Inicia el hilo que vigila vencimientos
    watcher_thread = threading.Thread(target=expiration_watcher, daemon=True)
    watcher_thread.start()

    # Registra tus handlers
    register_admin_handlers(bot)
    register_payments_handlers(bot)  # ⬅️ habilita /planes y el flujo de compra

    # Iniciar el polling infinito para escuchar mensajes
    bot.infinity_polling()
