# main.py

from telebot import TeleBot
import subprocess
import os

from config import BOT_TOKEN, ADMIN_ID, SCRIPT_PATH, CLIENTS_DIR
from admin_handlers import register_admin_handlers  # ✅ Importar handlers de admin

bot = TeleBot(BOT_TOKEN)

def is_admin(user_id):
    return user_id == ADMIN_ID

@bot.message_handler(func=lambda m: m.text == '📦 Crear cliente')
def solicitar_nombre_cliente(message):
    if not is_admin(message.from_user.id):
        return
    msg = bot.send_message(message.chat.id, "📅 Indica el *nombre del nuevo cliente*:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, crear_cliente)

def crear_cliente(message):
    if not is_admin(message.from_user.id):
        return

    client_name = message.text.strip()
    if not client_name:
        return bot.send_message(message.chat.id, "❌ Nombre no válido.")

    bot.send_message(message.chat.id, f"🔧 Generando configuración para *{client_name}*...", parse_mode="Markdown")

    try:
        result = subprocess.run(["sudo", "bash", SCRIPT_PATH, client_name], capture_output=True, text=True)

        if result.returncode != 0:
            return bot.send_message(message.chat.id, f"❌ Error: {result.stderr}")

        file_path = os.path.join(CLIENTS_DIR, f"{client_name}.conf")
        qr_path = os.path.join(CLIENTS_DIR, f"{client_name}.png")

        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"📄 Archivo de *{client_name}*", parse_mode="Markdown")

        if os.path.exists(qr_path):
            with open(qr_path, 'rb') as qr:
                bot.send_photo(message.chat.id, qr, caption=f"📷 QR de conexión para *{client_name}*", parse_mode="Markdown")

        bot.send_message(message.chat.id, "✅ Cliente creado correctamente.")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(func=lambda m: m.text == '📁 Ver archivos')
def listar_archivos(message):
    if not is_admin(message.from_user.id):
        return
    files = os.listdir(CLIENTS_DIR)
    if not files:
        return bot.send_message(message.chat.id, "📂 No hay archivos generados.")
    
    for file in files:
        path = os.path.join(CLIENTS_DIR, file)
        if file.endswith(".conf"):
            with open(path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"📄 {file}")
        elif file.endswith(".png"):
            with open(path, 'rb') as f:
                bot.send_photo(message.chat.id, f, caption=f"🖼️ {file}")

# ✅ Registrar los handlers de admin
register_admin_handlers(bot)

if __name__ == '__main__':
    bot.infinity_polling()
