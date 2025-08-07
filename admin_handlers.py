# admin_handlers.py

import os
from datetime import datetime
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from config import ADMIN_ID, PLANS, CLIENTS_DIR
from storage import load_json, save_json
from utils import generate_qr, renew_config, delete_config, get_stats, calcular_nuevo_vencimiento
from generator import create_config

# Usamos la misma carpeta de CLIENTS_DIR para almacenar el JSON
CONFIGS_FILE = os.path.join(CLIENTS_DIR, 'configuraciones.json')

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton('➕ Crear configuración'),
        KeyboardButton('🛠 Gestionar configuraciones'),
        KeyboardButton('📊 Estadísticas'),
        KeyboardButton('🔙 Volver')
    )
    return kb

def gestion_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton('🗂 Ver todas'),
        KeyboardButton('📆 Por expirar'),
        KeyboardButton('♻️ Renovar'),
        KeyboardButton('❌ Eliminar'),
        KeyboardButton('📁 Ver QR'),
        KeyboardButton('📄 Descargar .conf'),
        KeyboardButton('🔙 Menú admin')
    )
    return kb

# Almacenamos el estado temporal en memoria
TEMP = {}

def register_admin_handlers(bot: TeleBot):

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        if message.from_user.id != ADMIN_ID:
            return bot.send_message(message.chat.id, "⛔️ Acceso restringido.")
        text = (
            "👋 *Panel de Administración Francho Wire Bot*\n\n"
            "Gestiona tus clientes WireGuard de forma rápida:\n"
            "• ➕ Crear configuración\n"
            "• 🛠 Gestionar configuraciones\n"
            "• 📊 Estadísticas\n"
            "• 🔙 Volver\n\n"
            "Selecciona una opción."
        )
        bot.send_message(
            message.chat.id, text,
            parse_mode="Markdown",
            reply_markup=admin_menu()
        )

    @bot.message_handler(func=lambda m: m.text == '🛠 Gestionar configuraciones')
    def handle_gestionar(message):
        bot.send_message(
            message.chat.id,
            "🔧 *Gestión de Configuraciones*\nElige una acción:",
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

    #
    # —— Crear configuración —— 
    #
    @bot.message_handler(func=lambda m: m.text == '➕ Crear configuración')
    def iniciar_creacion(message):
        bot.send_message(
            message.chat.id,
            "✍️ *Escribe el nombre del cliente*:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, solicitar_plan)

    def solicitar_plan(message):
        TEMP[message.chat.id] = {'cliente': message.text.strip()}
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for plan in PLANS:
            kb.add(KeyboardButton(plan))
        kb.add(KeyboardButton('🔙 Volver'))
        bot.send_message(
            message.chat.id,
            "📦 *Selecciona un plan de duración*:",
            parse_mode="Markdown",
            reply_markup=kb
        )
        bot.register_next_step_handler(message, confirmar_creacion)

    def confirmar_creacion(message):
        if message.text == '🔙 Volver':
            TEMP.pop(message.chat.id, None)
            return bot.send_message(
                message.chat.id,
                "↩️ Regresando al menú principal.",
                reply_markup=admin_menu()
            )
        data = TEMP.get(message.chat.id, {})
        cliente = data.get('cliente')
        plan = message.text
        if plan not in PLANS:
            return bot.send_message(
                message.chat.id,
                "❌ Plan inválido, intenta de nuevo.",
                reply_markup=admin_menu()
            )
        venc = calcular_nuevo_vencimiento(plan)
        success, conf_path, qr_path = create_config(cliente, venc)
        if not success:
            return bot.send_message(
                message.chat.id,
                f"❌ Error: {conf_path}",
                reply_markup=admin_menu()
            )
        caption = (
            f"✅ *{cliente}* creado.\n"
            f"📅 Vence el: *{venc.strftime('%d/%m/%Y %H:%M')}*"
        )
        with open(conf_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=caption, parse_mode="Markdown")
        with open(qr_path, 'rb') as qr:
            bot.send_photo(message.chat.id, qr)
        TEMP.pop(message.chat.id, None)
        bot.send_message(
            message.chat.id,
            "↩️ Regresando al menú principal.",
            reply_markup=admin_menu()
        )

    #
    # —— Ver todas —— 
    #
    @bot.message_handler(func=lambda m: m.text == '🗂 Ver todas')
    def ver_todas(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "ℹ️ No hay configuraciones.")
        lines = ["📁 *Configuraciones registradas:*"]
        for cli, info in datos.items():
            estado = "✅ Activa" if info['activa'] else "⛔️ Expirada"
            lines.append(f"• {cli}: {estado} — vence {info['vencimiento']}")
        bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")

    #
    # —— Por expirar —— 
    #
    @bot.message_handler(func=lambda m: m.text == '📆 Por expirar')
    def por_expirar(message):
        datos = load_json(CONFIGS_FILE)
        proximas = []
        ahora = datetime.now()
        for cli, info in datos.items():
            vendt = datetime.strptime(info['vencimiento'], "%Y-%m-%d %H:%M:%S")
            dias = (vendt - ahora).days
            if 0 <= dias <= 3:
                proximas.append((cli, dias))
        if not proximas:
            return bot.send_message(message.chat.id, "✅ No hay configuraciones próximas a expirar.")
        lines = ["📆 *Por expirar en próximos 3 días:*"]
        for cli, dias in proximas:
            lines.append(f"• {cli}: vence en {dias} día(s)")
        bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")

    #
    # —— Renovar —— 
    #
    @bot.message_handler(func=lambda m: m.text == '♻️ Renovar')
    def renew_menu(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "ℹ️ No hay configuraciones para renovar.", reply_markup=admin_menu())
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for cli in datos.keys():
            kb.add(KeyboardButton(cli))
        kb.add(KeyboardButton('🔙 Menú admin'))
        bot.send_message(message.chat.id, "♻️ Selecciona un cliente a renovar:", reply_markup=kb)
        bot.register_next_step_handler(message, ejecutar_renovacion)

    def ejecutar_renovacion(message):
        if message.text == '🔙 Menú admin':
            return bot.send_message(message.chat.id, "↩️ Menú principal.", reply_markup=admin_menu())
        cliente = message.text.strip()
        exito, nuevo = renew_config(cliente)
        if exito:
            bot.send_message(
                message.chat.id,
                f"♻️ *{cliente}* renovado hasta {nuevo.strftime('%d/%m/%Y %H:%M')}",
                parse_mode="Markdown",
                reply_markup=admin_menu()
            )
        else:
            bot.send_message(message.chat.id, "❌ No se pudo renovar.", reply_markup=admin_menu())

    #
    # —— Eliminar —— 
    #
    @bot.message_handler(func=lambda m: m.text == '❌ Eliminar')
    def delete_menu(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "ℹ️ No hay configuraciones para eliminar.", reply_markup=admin_menu())
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for cli in datos.keys():
            kb.add(KeyboardButton(cli))
        kb.add(KeyboardButton('🔙 Menú admin'))
        bot.send_message(message.chat.id, "❌ Selecciona un cliente a eliminar:", reply_markup=kb)
        bot.register_next_step_handler(message, ejecutar_eliminacion)

    def ejecutar_eliminacion(message):
        if message.text == '🔙 Menú admin':
            return bot.send_message(message.chat.id, "↩️ Menú principal.", reply_markup=admin_menu())
        cliente = message.text.strip()
        if delete_config(cliente):
            bot.send_message(message.chat.id, f"🗑️ *{cliente}* eliminado.", parse_mode="Markdown", reply_markup=admin_menu())
        else:
            bot.send_message(message.chat.id, "❌ No se encontró el cliente.", reply_markup=admin_menu())

    #
    # —— Ver QR —— 
    #
    @bot.message_handler(func=lambda m: m.text == '📁 Ver QR')
    def qr_menu(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "ℹ️ No hay configuraciones.", reply_markup=admin_menu())
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for cli in datos.keys():
            kb.add(KeyboardButton(cli))
        kb.add(KeyboardButton('🔙 Menú admin'))
        bot.send_message(message.chat.id, "📁 Selecciona un cliente para ver su QR:", reply_markup=kb)
        bot.register_next_step_handler(message, enviar_qr_selection)

    def enviar_qr_selection(message):
        if message.text == '🔙 Menú admin':
            return bot.send_message(message.chat.id, "↩️ Menú principal.", reply_markup=admin_menu())
        cliente = message.text.strip()
        qr_path = os.path.join(CLIENTS_DIR, f"{cliente}.png")
        if os.path.exists(qr_path):
            with open(qr_path, 'rb') as qr:
                bot.send_photo(message.chat.id, qr, caption=f"📸 QR de *{cliente}*", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ QR no encontrado.", reply_markup=admin_menu())

    #
    # —— Descargar .conf —— 
    #
    @bot.message_handler(func=lambda m: m.text == '📄 Descargar .conf')
    def conf_menu(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "ℹ️ No hay configuraciones.", reply_markup=admin_menu())
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for cli in datos.keys():
            kb.add(KeyboardButton(cli))
        kb.add(KeyboardButton('🔙 Menú admin'))
        bot.send_message(message.chat.id, "📄 Selecciona un cliente para descargar su .conf:", reply_markup=kb)
        bot.register_next_step_handler(message, enviar_conf_selection)

    def enviar_conf_selection(message):
        if message.text == '🔙 Menú admin':
            return bot.send_message(message.chat.id, "↩️ Menú principal.", reply_markup=admin_menu())
        cliente = message.text.strip()
        conf_path = os.path.join(CLIENTS_DIR, f"{cliente}.conf")
        if os.path.exists(conf_path):
            with open(conf_path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"📄 *{cliente}*", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ .conf no encontrado.", reply_markup=admin_menu())

Qué hace este cambio

Ahora CONFIGS_FILE es un JSON dentro de la carpeta CLIENTS_DIR, por lo que carga y guarda ahí las configuraciones.

En los flujos de Renovar, Eliminar, Ver QR y Descargar .conf, en lugar de pedir texto libre, el bot te muestra un teclado con los nombres de cliente disponibles y un botón de “🔙 Menú admin”.

Asegúrate de que exista el archivo JSON (puedes crearlo vacío con {}) y de que storage.load_json y storage.save_json usen la misma ruta.


Con esto, al pulsar “🛠 Gestionar configuraciones” y luego “♻️ Renovar” (o cualquier otra acción), verás directamente los clientes disponibles como botones.

