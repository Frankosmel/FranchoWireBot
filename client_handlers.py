# client_handlers.py

from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from config import CLIENTES_DIR
from utils import ruta_conf_cliente, generar_qr_desde_conf, cargar_cliente
import os

def mostrar_menu_cliente(bot: TeleBot, chat_id: int):
    """
    Muestra el menú principal para clientes registrados.
    """
    if not cliente_existe(chat_id):
        return bot.send_message(chat_id, "❌ No estás registrado como cliente.\nContacta con el administrador para obtener tu configuración.")

    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("📁 Ver configuración"),
        KeyboardButton("📅 Ver vencimiento"),
        KeyboardButton("📷 Ver código QR")
    )
    bot.send_message(chat_id, "📲 *Panel de Cliente Francho Wire Bot*\n\nSelecciona una opción:", reply_markup=kb, parse_mode="Markdown")

def cliente_existe(chat_id: int) -> bool:
    """
    Verifica si el archivo del cliente existe por su ID.
    """
    ruta = os.path.join(CLIENTES_DIR, f"{chat_id}.json")
    return os.path.exists(ruta)

def manejar_respuesta_cliente(bot: TeleBot, message):
    """
    Maneja las respuestas del cliente desde el menú.
    """
    chat_id = message.chat.id
    if not cliente_existe(chat_id):
        return bot.send_message(chat_id, "❌ No estás registrado como cliente.\nSolicita tu configuración al administrador.")

    texto = message.text.strip()

    if texto == "📁 Ver configuración":
        ruta = ruta_conf_cliente(str(chat_id))
        if not os.path.exists(ruta):
            return bot.send_message(chat_id, "⚠️ No se encontró tu archivo de configuración.")
        with open(ruta, "rb") as archivo:
            bot.send_document(chat_id, archivo, caption="📄 Aquí tienes tu archivo de configuración WireGuard.")

    elif texto == "📅 Ver vencimiento":
        datos = cargar_cliente(str(chat_id))
        if not datos:
            return bot.send_message(chat_id, "⚠️ No se pudo obtener la información de vencimiento.")
        bot.send_message(chat_id, f"📆 Tu configuración vence el:\n*{datos['vencimiento']}*", parse_mode="Markdown")

    elif texto == "📷 Ver código QR":
        ruta = ruta_conf_cliente(str(chat_id))
        if not os.path.exists(ruta):
            return bot.send_message(chat_id, "⚠️ No se encontró tu archivo de configuración.")
        qr = generar_qr_desde_conf(ruta)
        if qr:
            bot.send_photo(chat_id, qr, caption="📷 Código QR de tu configuración")
        else:
            bot.send_message(chat_id, "❌ No se pudo generar el código QR.")
