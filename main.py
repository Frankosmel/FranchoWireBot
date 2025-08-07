# main.py

from telebot import TeleBot
import subprocess
import os

from config import (
    BOT_TOKEN,
    ADMIN_ID,
    SCRIPT_PATH,
    CLIENTS_DIR
)
from admin_handlers import register_admin_handlers  # ✅ Importar handlers de admin

# Inicializar bot de Telegram
bot = TeleBot(BOT_TOKEN)

# Registrar todos los handlers de administración
register_admin_handlers(bot)

if __name__ == '__main__':
    # Iniciar el polling infinito para escuchar mensajes
    bot.infinity_polling()
