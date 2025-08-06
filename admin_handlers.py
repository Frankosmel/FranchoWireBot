# admin_handlers.py

from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import ADMIN_ID, CLIENTES_DIR, PLANES
from utils import generar_qr_desde_conf, calcular_vencimiento, ruta_conf_cliente
import os
import json
from datetime import datetime, timedelta

# Diccionario para controlar el flujo de creación
CREACION = {}

# ========================= MENÚ PRINCIPAL DEL ADMIN =========================

def mostrar_menu_admin(bot: TeleBot, chat_id: int):
    if chat_id != ADMIN_ID:
        return
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("➕ Crear cliente"),
        KeyboardButton("📄 Ver clientes"),
        KeyboardButton("📊 Estadísticas"),
        KeyboardButton("🔄 Renovar cliente"),
        KeyboardButton("🗑️ Eliminar cliente")
    )
    bot.send_message(chat_id, "🔧 *Panel de Administración Francho Wire Bot*\n\nSelecciona una opción:", reply_markup=kb, parse_mode="Markdown")

# ========================= CREAR CLIENTE PASO A PASO =========================

def iniciar_creacion_cliente(bot: TeleBot, message):
    if message.chat.id != ADMIN_ID:
        return
    CREACION[message.chat.id] = {"estado": "esperando_nombre"}
    cancelar_opciones(bot, message.chat.id)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔙 Volver"))
    bot.send_message(message.chat.id, "✍️ Escribe el *nombre del cliente* que deseas crear:", reply_markup=kb, parse_mode="Markdown")

def manejar_respuesta_creacion(bot: TeleBot, message):
    chat_id = message.chat.id
    if chat_id != ADMIN_ID or chat_id not in CREACION:
        return

    if message.text == "🔙 Volver":
        CREACION.pop(chat_id, None)
        return mostrar_menu_admin(bot, chat_id)

    estado = CREACION[chat_id]["estado"]

    if estado == "esperando_nombre":
        nombre = message.text.strip()
        if not nombre:
            return bot.send_message(chat_id, "❌ El nombre no puede estar vacío.")
        CREACION[chat_id]["nombre"] = nombre
        CREACION[chat_id]["estado"] = "esperando_plan"

        # Mostrar opciones de planes
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for plan in PLANES.keys():
            kb.add(KeyboardButton(plan))
        kb.add(KeyboardButton("🔙 Volver"))
        return bot.send_message(chat_id, "📦 Selecciona un *plan de duración* para este cliente:", reply_markup=kb, parse_mode="Markdown")

    elif estado == "esperando_plan":
        if message.text not in PLANES:
            return bot.send_message(chat_id, "❌ Plan no válido. Selecciona uno de la lista.")
        CREACION[chat_id]["plan"] = message.text

        # Ejecutar script externo
        nombre = CREACION[chat_id]["nombre"]
        ruta_script = os.path.abspath("crear_cliente.sh")
        os.system(f"sudo bash {ruta_script} {nombre}")

        ruta_archivo = ruta_conf_cliente(nombre)
        if not os.path.exists(ruta_archivo):
            return bot.send_message(chat_id, "⚠️ Hubo un error al generar el archivo de configuración.")

        # Guardar metadatos del cliente
        vencimiento = calcular_vencimiento(PLANES[message.text])
        guardar_cliente(nombre, message.text, vencimiento)

        # Enviar resultado al admin
        with open(ruta_archivo, "rb") as doc:
            bot.send_document(chat_id, doc, caption=f"✅ Cliente creado: *{nombre}*\n📅 Vence: {vencimiento}", parse_mode="Markdown")

        # Enviar QR
        qr = generar_qr_desde_conf(ruta_archivo)
        if qr:
            bot.send_photo(chat_id, qr)

        CREACION.pop(chat_id, None)
        mostrar_menu_admin(bot, chat_id)

# ========================= UTILIDADES =========================

def cancelar_opciones(bot: TeleBot, chat_id: int):
    kb = ReplyKeyboardRemove()
    bot.send_message(chat_id, "ℹ️ Cancelando flujo anterior...", reply_markup=kb)

def guardar_cliente(nombre: str, plan: str, vencimiento: str):
    datos = {
        "plan": plan,
        "vencimiento": vencimiento,
        "creado": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    os.makedirs(CLIENTES_DIR, exist_ok=True)
    with open(os.path.join(CLIENTES_DIR, f"{nombre}.json"), "w") as f:
        json.dump(datos, f, indent=2)
