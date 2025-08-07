# admin_handlers.py

from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from config import ADMIN_ID, PLANS
from storage import load_json, save_json
from utils import generate_qr, renew_config, delete_config, get_stats
from generator import create_config
from datetime import datetime, timedelta
import os

CONFIGS_FILE = 'data/configuraciones.json'

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

# Temporal storage for multi-step flows
TEMP = {}

def register_admin_handlers(bot: TeleBot):

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        if message.from_user.id != ADMIN_ID:
            return bot.send_message(message.chat.id, "⛔️ Acceso restringido.")

        # Detailed welcome and instructions
        text = (
            "👋 *Bienvenido al Panel de Administración de Francho Wire Bot*\n\n"
            "Con este bot podrás gestionar tus clientes WireGuard de manera sencilla:\n"
            "• ➕ Crear configuración: Genera archivos .conf y códigos QR.\n"
            "• 🛠 Gestionar configuraciones: Ver, renovar o eliminar configuraciones.\n"
            "• 📊 Estadísticas: Consulta cuántos clientes están activos o expirados.\n"
            "• 🔙 Volver: Regresa al menú principal en cualquier momento.\n\n"
            "Selecciona una opción para comenzar."
        )
        bot.send_message(
            message.chat.id,
            text,
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
        cliente = message.text.strip()
        TEMP[message.chat.id] = {'cliente': cliente}
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
        # calculate expiration
        delta = PLANS[plan]
        venc = datetime.now() + timedelta(**delta)
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
        # send files
        with open(conf_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=caption, parse_mode="Markdown")
        with open(qr_path, 'rb') as qr:
            bot.send_photo(message.chat.id, qr)
        TEMP.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "↩️ Regresando al menú principal.", reply_markup=admin_menu())

    @bot.message_handler(func=lambda m: m.text == '🗂 Ver todas')
    def ver_todas(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "ℹ️ No hay configuraciones registradas.")
        lines = ["📁 *Configuraciones registradas:*"]
        for cli, info in datos.items():
            estado = "✅ Activa" if info['activa'] else "⛔️ Expirada"
            lines.append(f"• {cli}: {estado} — vence {info['vencimiento']}")
        bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")

    @bot.message_handler(func=lambda m: m.text == '📆 Por expirar')
    def por_expirar(message):
        datos = load_json(CONFIGS_FILE)
        proximas = []
        hoy = datetime.now()
        for cli, info in datos.items():
            vendt = datetime.strptime(info['vencimiento'], "%Y-%m-%d %H:%M:%S")
            dias = (vendt - hoy).days
            if 0 <= dias <= 3:
                proximas.append((cli, dias))
        if not proximas:
            return bot.send_message(message.chat.id, "✅ No hay configuraciones próximas a expirar.")
        lines = ["📆 *Por expirar en los próximos 3 días:*"]
        for cli, dias in proximas:
            lines.append(f"• {cli}: vence en {dias} día(s)")
        bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")

    @bot.message_handler(func=lambda m: m.text == '📁 Ver QR')
    def ver_qr(message):
        bot.send_message(
            message.chat.id,
            "✏️ *Nombre del cliente* para ver QR:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, enviar_qr)

    def enviar_qr(message):
        cliente = message.text.strip()
        path = f"data/clientes/{cliente}.png"
        if not os.path.exists(path):
            return bot.send_message(message.chat.id, "❌ QR no encontrado.")
        with open(path, 'rb') as qr:
            bot.send_photo(message.chat.id, qr, caption=f"📸 QR de *{cliente}*", parse_mode="Markdown")

    @bot.message_handler(func=lambda m: m.text == '📄 Descargar .conf')
    def ver_conf(message):
        bot.send_message(
            message.chat.id,
            "✏️ *Nombre del cliente* para .conf:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, enviar_conf)

    def enviar_conf(message):
        cliente = message.text.strip()
        path = f"data/clientes/{cliente}.conf"
        if not os.path.exists(path):
            return bot.send_message(message.chat.id, "❌ .conf no encontrado.")
        with open(path, 'rb') as conf:
            bot.send_document(message.chat.id, conf, caption=f"📄 *{cliente}*", parse_mode="Markdown")

    @bot.message_handler(func=lambda m: m.text == '♻️ Renovar')
    def renovar(message):
        bot.send_message(
            message.chat.id,
            "✏️ *Nombre del cliente* a renovar:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, ejecutar_renovacion)

    def ejecutar_renovacion(message):
        cliente = message.text.strip()
        exito, nuevo = renew_config(cliente)
        if exito:
            bot.send_message(
                message.chat.id,
                f"♻️ *{cliente}* renovado hasta {nuevo.strftime('%d/%m/%Y')}",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(message.chat.id, "❌ No se pudo renovar. Verifica el nombre.")

    @bot.message_handler(func=lambda m: m.text == '❌ Eliminar')
    def eliminar(message):
        bot.send_message(
            message.chat.id,
            "✏️ *Nombre del cliente* a eliminar:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, ejecutar_eliminacion)

    def ejecutar_eliminacion(message):
        cliente = message.text.strip()
        if delete_config(cliente):
            bot.send_message(message.chat.id, f"🗑️ *{cliente}* eliminado.", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ No se pudo eliminar. Verifica el nombre.")
```0
