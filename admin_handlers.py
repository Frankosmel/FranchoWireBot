# admin_handlers.py

import os
from datetime import datetime
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from config import ADMIN_ID, PLANS
from storage import load_json, save_json
from utils import renew_config, generate_qr, calcular_nuevo_vencimiento
from generator import create_config

# Rutas y constantes
CONFIGS_FILE = os.path.join('data', 'configuraciones.json')
CLIENTS_DIR  = os.path.join('data', 'clientes')

# Estados pendientes por chat_id
PENDING_ACTION = {}
# Almacena datos temporales (por ejemplo, el cliente seleccionado)
TEMP = {}

def make_clients_keyboard():
    """Genera un teclado con todos los clientes registrados."""
    datos = load_json(CONFIGS_FILE) or {}
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for cliente in datos.keys():
        kb.add(KeyboardButton(cliente))
    kb.add(KeyboardButton('🔙 Menú admin'))
    return kb

def admin_menu():
    """Teclado del menú principal de administrador."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton('➕ Crear configuración'),
        KeyboardButton('🛠 Gestionar configuraciones'),
        KeyboardButton('📊 Estadísticas'),
        KeyboardButton('🔙 Salir')
    )
    return kb

def gestion_menu():
    """Teclado de las acciones de gestión."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton('♻️ Renovar'),
        KeyboardButton('📁 Ver QR'),
        KeyboardButton('❌ Eliminar'),
        KeyboardButton('🔙 Menú admin')
    )
    return kb

def register_admin_handlers(bot: TeleBot):
    """Registra todos los handlers de administración en el bot."""

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        if message.from_user.id != ADMIN_ID:
            return bot.send_message(message.chat.id, "⛔️ Acceso restringido.")
        bot.send_message(
            message.chat.id,
            "👋 *Bienvenido al Panel de Administración*",
            parse_mode="Markdown",
            reply_markup=admin_menu()
        )

    @bot.message_handler(func=lambda m: m.text == '➕ Crear configuración')
    def prompt_create(message):
        PENDING_ACTION[message.chat.id] = 'create_name'
        bot.send_message(
            message.chat.id,
            "✍️ *Escribe el nombre del cliente*:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )

    @bot.message_handler(func=lambda m: PENDING_ACTION.get(m.chat.id) == 'create_name')
    def handle_create_name(message):
        nombre = message.text.strip()
        TEMP[message.chat.id] = {'cliente': nombre}
        PENDING_ACTION[message.chat.id] = 'create_plan'
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for plan in PLANS.keys():
            kb.add(KeyboardButton(plan))
        kb.add(KeyboardButton('🔙 Menú admin'))
        bot.send_message(
            message.chat.id,
            f"📦 Cliente *{nombre}*.\nSelecciona un *plan de duración*:",
            parse_mode="Markdown",
            reply_markup=kb
        )

    @bot.message_handler(func=lambda m: PENDING_ACTION.get(m.chat.id) == 'create_plan')
    def handle_create_plan(message):
        if message.text == '🔙 Menú admin':
            PENDING_ACTION.pop(message.chat.id, None)
            TEMP.pop(message.chat.id, None)
            return bot.send_message(message.chat.id, "↩️ Volviendo al menú principal.", reply_markup=admin_menu())
        plan = message.text
        cliente = TEMP[message.chat.id]['cliente']
        if plan not in PLANS:
            return bot.send_message(message.chat.id, "❌ Plan inválido.", reply_markup=admin_menu())
        venc = calcular_nuevo_vencimiento(plan)
        success, conf_path, qr_path = create_config(cliente, venc)
        if not success:
            return bot.send_message(message.chat.id, f"❌ Error: {conf_path}", reply_markup=admin_menu())
        # Guardar en JSON de configuraciones
        data = load_json(CONFIGS_FILE) or {}
        data[cliente] = {
            'vencimiento': venc.strftime("%Y-%m-%d %H:%M:%S"),
            'activa': True,
            'plan': plan
        }
        save_json(CONFIGS_FILE, data)
        # Enviar archivos
        caption = (
            f"✅ *{cliente}* creado.\n"
            f"📅 Vence el: *{venc.strftime('%d/%m/%Y %I:%M %p')}*"
        )
        with open(conf_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=caption, parse_mode="Markdown")
        with open(qr_path, 'rb') as qr:
            bot.send_photo(message.chat.id, qr)
        # Limpieza y retorno
        PENDING_ACTION.pop(message.chat.id, None)
        TEMP.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "↩️ Volviendo al menú principal.", reply_markup=admin_menu())

    @bot.message_handler(func=lambda m: m.text == '🛠 Gestionar configuraciones')
    def prompt_gestionar(message):
        bot.send_message(
            message.chat.id,
            "🔧 *Gestión de Configuraciones*",
            parse_mode="Markdown",
            reply_markup=gestion_menu()
        )

    @bot.message_handler(func=lambda m: m.text == '📊 Estadísticas')
    def handle_stats(message):
        activos, expirados = get_stats()
        total = activos + expirados
        msg = (
            f"📊 *Estadísticas del sistema:*\n\n"
            f"✅ Activas: {activos}\n"
            f"⛔️ Expiradas: {expirados}\n"
            f"📦 Total: {total}"
        )
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    @bot.message_handler(func=lambda m: m.text == '♻️ Renovar')
    def prompt_renew(message):
        PENDING_ACTION[message.chat.id] = 'renew_select'
        bot.send_message(
            message.chat.id,
            "♻️ *Selecciona cliente a renovar*:",
            parse_mode="Markdown",
            reply_markup=make_clients_keyboard()
        )

    @bot.message_handler(func=lambda m: m.text == '📁 Ver QR')
    def prompt_qr(message):
        PENDING_ACTION[message.chat.id] = 'qr'
        bot.send_message(
            message.chat.id,
            "📁 *Selecciona cliente para ver QR*:",
            parse_mode="Markdown",
            reply_markup=make_clients_keyboard()
        )

    @bot.message_handler(func=lambda m: m.text == '❌ Eliminar')
    def prompt_delete(message):
        PENDING_ACTION[message.chat.id] = 'delete'
        bot.send_message(
            message.chat.id,
            "🗑️ *Selecciona cliente a eliminar*:",
            parse_mode="Markdown",
            reply_markup=make_clients_keyboard()
        )

    @bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text and load_json(CONFIGS_FILE) and m.text in load_json(CONFIGS_FILE))
    def handle_client_selection(message):
        action = PENDING_ACTION.get(message.chat.id)
        cliente = message.text
        # Botón de volver
        if cliente == '🔙 Menú admin':
            PENDING_ACTION.pop(message.chat.id, None)
            TEMP.pop(message.chat.id, None)
            return bot.send_message(message.chat.id, "↩️ Volviendo al menú de gestión.", reply_markup=gestion_menu())

        # Procesar según acción
        if action == 'renew_select':
            TEMP[message.chat.id] = {'cliente': cliente}
            PENDING_ACTION[message.chat.id] = 'renew_plan'
            kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for plan in PLANS.keys():
                kb.add(KeyboardButton(plan))
            kb.add(KeyboardButton('🔙 Menú admin'))
            return bot.send_message(
                message.chat.id,
                f"♻️ Cliente *{cliente}* seleccionado.\nElige cuánto tiempo añadir:",
                parse_mode="Markdown",
                reply_markup=kb
            )

        if action == 'renew_plan':
            if message.text == '🔙 Menú admin':
                PENDING_ACTION.pop(message.chat.id, None)
                TEMP.pop(message.chat.id, None)
                return bot.send_message(message.chat.id, "↩️ Volviendo al menú de gestión.", reply_markup=gestion_menu())
            plan = message.text
            cliente = TEMP[message.chat.id]['cliente']
            if plan not in PLANS:
                return bot.send_message(message.chat.id, "❌ Plan inválido.", reply_markup=gestion_menu())
            exito, nueva_fecha = renew_config(cliente, plan)
            PENDING_ACTION.pop(message.chat.id, None)
            TEMP.pop(message.chat.id, None)
            if exito:
                return bot.send_message(
                    message.chat.id,
                    f"♻️ *{cliente}* renovado hasta {nueva_fecha.strftime('%d/%m/%Y %I:%M %p')}",
                    parse_mode="Markdown",
                    reply_markup=gestion_menu()
                )
            else:
                return bot.send_message(message.chat.id, "❌ No se pudo renovar.", reply_markup=gestion_menu())

        if action == 'qr':
            qr_path = os.path.join(CLIENTS_DIR, f"{cliente}.png")
            PENDING_ACTION.pop(message.chat.id, None)
            if os.path.exists(qr_path):
                with open(qr_path, 'rb') as qr:
                    bot.send_photo(message.chat.id, qr, caption=f"📸 QR de *{cliente}*", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "❌ QR no encontrado.")
            return bot.send_message(message.chat.id, "↩️ Volviendo al menú de gestión.", reply_markup=gestion_menu())

        if action == 'delete':
            PENDING_ACTION.pop(message.chat.id, None)
            if delete_config(cliente):
                bot.send_message(message.chat.id, f"🗑️ *{cliente}* eliminado.", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "❌ No se pudo eliminar.")
            return bot.send_message(message.chat.id, "↩️ Volviendo al menú de gestión.", reply_markup=gestion_menu())
