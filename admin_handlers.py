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

# Funciones auxiliares para teclado

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add('🛠 Gestionar configuraciones')
    kb.add('➕ Crear configuración', '📊 Estadísticas')
    kb.add('🔙 Volver')
    return kb

def gestion_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add('🗂 Ver todas', '📆 Por expirar')
    kb.add('♻️ Renovar', '❌ Eliminar')
    kb.add('📁 Ver QR', '📄 Descargar .conf')
    kb.add('🔙 Menú admin')
    return kb

# Variables temporales
TEMP = {}

def register_admin_handlers(bot: TeleBot):

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        if message.from_user.id != ADMIN_ID:
            return bot.send_message(message.chat.id, "⛔ Acceso restringido.")
        bot.send_message(message.chat.id, "👋 Bienvenido al panel de administrador", reply_markup=admin_menu())

    @bot.message_handler(func=lambda m: m.text == '🛠 Gestionar configuraciones')
    def handle_gestionar(message):
        bot.send_message(message.chat.id, "Elige una opción:", reply_markup=gestion_menu())

    @bot.message_handler(func=lambda m: m.text == '📊 Estadísticas')
    def handle_stats(message):
        activos, expirados = get_stats()
        total = activos + expirados
        msg = f"📊 Estadísticas del sistema:\n\n"
        msg += f"✅ Activas: {activos}\n"
        msg += f"⛔ Expiradas: {expirados}\n"
        msg += f"📦 Total: {total}"
        bot.send_message(message.chat.id, msg)

    @bot.message_handler(func=lambda m: m.text == '➕ Crear configuración')
    def crear_config(message):
        msg = bot.send_message(message.chat.id, "🧑‍💻 Escribe el *nombre del cliente*:", reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
        bot.register_next_step_handler(msg, solicitar_plan)

    def solicitar_plan(message):
        TEMP[message.chat.id] = {'cliente': message.text}
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for plan in PLANS.keys():
            kb.add(plan)
        msg = bot.send_message(message.chat.id, "📦 Elige un *plan de duración*:", reply_markup=kb, parse_mode="Markdown")
        bot.register_next_step_handler(msg, confirmar_creacion)

    def confirmar_creacion(message):
        user_data = TEMP.get(message.chat.id, {})
        cliente = user_data.get('cliente')
        plan = message.text
        if plan not in PLANS:
            return bot.send_message(message.chat.id, "❌ Plan inválido. Intenta nuevamente.", reply_markup=admin_menu())
        dias = PLANS[plan]
        vencimiento = datetime.now() + timedelta(days=dias)
        success, path, qr_path = create_config(cliente, vencimiento)
        if not success:
            return bot.send_message(message.chat.id, f"❌ Error al crear: {path}", reply_markup=admin_menu())
        msg = f"✅ Cliente *{cliente}* creado.\n"
        msg += f"📅 Vence el: *{vencimiento.strftime('%d/%m/%Y')}*"
        with open(qr_path, 'rb') as qr:
            bot.send_photo(message.chat.id, qr, caption=msg, parse_mode="Markdown")
        TEMP.pop(message.chat.id, None)

    @bot.message_handler(func=lambda m: m.text == '🗂 Ver todas')
    def ver_todas(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "📂 No hay configuraciones registradas.")
        msg = "📁 Configuraciones registradas:\n\n"
        for cliente, info in datos.items():
            estado = "✅ Activa" if info['activa'] else "⛔ Expirada"
            msg += f"👤 {cliente} — {estado}\n"
        bot.send_message(message.chat.id, msg)

    @bot.message_handler(func=lambda m: m.text == '📆 Por expirar')
    def por_expirar(message):
        datos = load_json(CONFIGS_FILE)
        ahora = datetime.now()
        proximas = []
        for cliente, info in datos.items():
            vencimiento = datetime.strptime(info['vencimiento'], "%Y-%m-%d")
            dias = (vencimiento - ahora).days
            if 0 <= dias <= 3:
                proximas.append((cliente, dias))
        if not proximas:
            return bot.send_message(message.chat.id, "✅ No hay configuraciones por expirar pronto.")
        msg = "📆 Configuraciones próximas a expirar:\n\n"
        for cliente, dias in proximas:
            msg += f"👤 {cliente} — vence en {dias} día(s)\n"
        bot.send_message(message.chat.id, msg)

    @bot.message_handler(func=lambda m: m.text == '📁 Ver QR')
    def ver_qr(message):
        msg = bot.send_message(message.chat.id, "✏️ Escribe el *nombre del cliente* para ver el QR:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, enviar_qr)

    def enviar_qr(message):
        cliente = message.text
        path = f"data/clientes/{cliente}.png"
        if not os.path.exists(path):
            return bot.send_message(message.chat.id, "❌ No se encontró el archivo QR.")
        with open(path, 'rb') as qr:
            bot.send_photo(message.chat.id, qr, caption=f"📸 Código QR de *{cliente}*", parse_mode="Markdown")

    @bot.message_handler(func=lambda m: m.text == '📄 Descargar .conf')
    def ver_conf(message):
        msg = bot.send_message(message.chat.id, "✏️ Escribe el *nombre del cliente* para obtener el .conf:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, enviar_conf)

    def enviar_conf(message):
        cliente = message.text
        path = f"data/clientes/{cliente}.conf"
        if not os.path.exists(path):
            return bot.send_message(message.chat.id, "❌ No se encontró el archivo .conf.")
        with open(path, 'rb') as conf:
            bot.send_document(message.chat.id, conf, caption=f"📄 Archivo de configuración de *{cliente}*", parse_mode="Markdown")

    @bot.message_handler(func=lambda m: m.text == '♻️ Renovar')
    def renovar(message):
        msg = bot.send_message(message.chat.id, "✏️ Escribe el *nombre del cliente* a renovar:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, ejecutar_renovacion)

    def ejecutar_renovacion(message):
        cliente = message.text
        exito, nuevo_vencimiento = renew_config(cliente)
        if exito:
            return bot.send_message(message.chat.id, f"♻️ *{cliente}* renovado hasta {nuevo_vencimiento.strftime('%d/%m/%Y')}", parse_mode="Markdown")
        else:
            return bot.send_message(message.chat.id, "❌ No se pudo renovar. Verifica el nombre.")

    @bot.message_handler(func=lambda m: m.text == '❌ Eliminar')
    def eliminar(message):
        msg = bot.send_message(message.chat.id, "🗑 Escribe el *nombre del cliente* a eliminar:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, ejecutar_eliminacion)

    def ejecutar_eliminacion(message):
        cliente = message.text
        if delete_config(cliente):
            return bot.send_message(message.chat.id, f"🗑 *{cliente}* eliminado correctamente.", parse_mode="Markdown")
        else:
            return bot.send_message(message.chat.id, "❌ No se pudo eliminar. Verifica el nombre.")
