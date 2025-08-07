# admin_handlers.py

import os
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from datetime import datetime
import pytz

from config import ADMIN_ID, PLANS
from storage import load_json, save_json
from utils import generate_qr, renew_config, delete_config, get_stats, calcular_nuevo_vencimiento
from generator import create_config

# Donde guardamos el JSON con todas las configuraciones
CONFIGS_FILE = os.path.join('data', 'configuraciones.json')
# Zona horaria Cuba
TZ_CUBA = pytz.timezone('America/Havana')

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

# Estado temporal de flujos
TEMP = {}

def register_admin_handlers(bot: TeleBot):

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        if message.from_user.id != ADMIN_ID:
            return bot.send_message(message.chat.id, "⛔️ Acceso restringido.")
        texto = (
            "👋 *Bienvenido al Panel de Administración Francho Wire Bot*\n\n"
            "Gestiona tus clientes WireGuard:\n"
            "• ➕ Crear configuración\n"
            "• 🛠 Gestionar configuraciones\n"
            "• 📊 Estadísticas\n"
            "• 🔙 Volver\n\n"
            "Selecciona una opción."
        )
        bot.send_message(
            message.chat.id,
            texto,
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
        TEMP[message.chat.id] = {'cliente': message.text.strip()}
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for plan in PLANS:
            kb.add(KeyboardButton(plan))
        kb.add(KeyboardButton('🔙 Menú admin'))
        bot.send_message(
            message.chat.id,
            "📦 *Selecciona un plan de duración*:",
            parse_mode="Markdown",
            reply_markup=kb
        )
        bot.register_next_step_handler(message, confirmar_creacion)

    def confirmar_creacion(message):
        if message.text == '🔙 Menú admin':
            TEMP.pop(message.chat.id, None)
            return bot.send_message(
                message.chat.id,
                "↩️ Regresando al menú principal.",
                reply_markup=admin_menu()
            )
        data = TEMP.pop(message.chat.id, {})
        cliente = data['cliente']
        plan = message.text
        if plan not in PLANS:
            return bot.send_message(
                message.chat.id,
                "❌ Plan inválido.",
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
        # Formatear vencimiento en Cuba 12h
        local_venc = venc.astimezone(TZ_CUBA)
        venc_txt = local_venc.strftime("%d/%m/%Y %I:%M %p")
        caption = f"✅ *{cliente}* creado.\n📅 Vence el: *{venc_txt}*"
        with open(conf_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=caption, parse_mode="Markdown")
        with open(qr_path, 'rb') as qr:
            bot.send_photo(message.chat.id, qr)
        bot.send_message(
            message.chat.id,
            "↩️ Regresando al menú principal.",
            reply_markup=admin_menu()
        )

    @bot.message_handler(func=lambda m: m.text == '🗂 Ver todas')
    def ver_todas(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "ℹ️ No hay configuraciones.")
        lines = ["📁 *Configuraciones registradas:*"]
        for cli, info in datos.items():
            # Mostrar fecha en 12h Cuba
            dt = datetime.strptime(info['vencimiento'], "%Y-%m-%d %H:%M")
            dt = TZ_CUBA.localize(dt)
            venc_txt = dt.strftime("%d/%m/%Y %I:%M %p")
            estado = "✅ Activa" if dt > datetime.now(TZ_CUBA) else "⛔️ Expirada"
            lines.append(f"• {cli}: {estado} — vence {venc_txt}")
        bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")

    @bot.message_handler(func=lambda m: m.text == '📆 Por expirar')
    def por_expirar(message):
        datos = load_json(CONFIGS_FILE)
        proximas = []
        ahora = datetime.now(TZ_CUBA)
        for cli, info in datos.items():
            dt = datetime.strptime(info['vencimiento'], "%Y-%m-%d %H:%M")
            dt = TZ_CUBA.localize(dt)
            dias = (dt - ahora).days
            if 0 <= dias <= 3:
                venc_txt = dt.strftime("%d/%m/%Y %I:%M %p")
                proximas.append(f"• {cli}: vence en {dias} día(s) ({venc_txt})")
        if not proximas:
            return bot.send_message(message.chat.id, "✅ Sin expiraciones próximas.")
        msg = "📆 *Próximas a expirar en 3 días:*\n\n" + "\n".join(proximas)
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    @bot.message_handler(func=lambda m: m.text == '📁 Ver QR')
    def ver_qr(message):
        bot.send_message(
            message.chat.id, "✏️ *Nombre del cliente* para ver QR:", parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, enviar_qr)

    def enviar_qr(message):
        cliente = message.text.strip()
        path = os.path.join('data', 'clientes', f"{cliente}.png")
        if not os.path.exists(path):
            return bot.send_message(message.chat.id, "❌ QR no encontrado.")
        with open(path,'rb') as qr:
            bot.send_photo(message.chat.id, qr, caption=f"📸 QR de *{cliente}*")

    @bot.message_handler(func=lambda m: m.text == '📄 Descargar .conf')
    def ver_conf(message):
        bot.send_message(
            message.chat.id, "✏️ *Nombre del cliente* para .conf:", parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, enviar_conf)

    def enviar_conf(message):
        cliente = message.text.strip()
        path = os.path.join('data','clientes', f"{cliente}.conf")
        if not os.path.exists(path):
            return bot.send_message(message.chat.id, "❌ .conf no encontrado.")
        with open(path,'rb') as conf:
            bot.send_document(message.chat.id, conf, caption=f"📄 *{cliente}*")

    @bot.message_handler(func=lambda m: m.text == '♻️ Renovar')
    def renovar(message):
        # Igual que creación: pedir cliente → plan → confirmar
        bot.send_message(
            message.chat.id, "✏️ *Nombre del cliente* a renovar:", parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, renovar_solicitar_plan)

    def renovar_solicitar_plan(message):
        cliente = message.text.strip()
        TEMP[message.chat.id] = {'cliente': cliente}
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for plan in PLANS:
            kb.add(KeyboardButton(plan))
        kb.add(KeyboardButton('🔙 Menú admin'))
        bot.send_message(
            message.chat.id, "📦 *Selecciona un plan para renovar*:", parse_mode="Markdown", reply_markup=kb
        )
        bot.register_next_step_handler(message, confirmar_renovacion)

    def confirmar_renovacion(message):
        if message.text == '🔙 Menú admin':
            TEMP.pop(message.chat.id, None)
            return bot.send_message(message.chat.id, "↩️ Volviendo al menú.", reply_markup=admin_menu())
        data = TEMP.pop(message.chat.id, {})
        cliente = data['cliente']
        plan = message.text
        if plan not in PLANS:
            return bot.send_message(message.chat.id, "❌ Plan inválido.", reply_markup=admin_menu())
        # Extiende vencimiento
        success, nueva = renew_config(cliente)
        if not success:
            return bot.send_message(message.chat.id, "❌ No existe el cliente.", reply_markup=admin_menu())
        # Añade días/horas extra
        extra = PLANS[plan]
        nueva = nueva + timedelta(**extra)
        # Guarda de nuevo
        save_json(CONFIGS_FILE, cliente, {
            **load_json(CONFIGS_FILE)[cliente],
            'vencimiento': nueva.strftime("%Y-%m-%d %H:%M")
        })
        local_nueva = nueva.astimezone(TZ_CUBA).strftime("%d/%m/%Y %I:%M %p")
        bot.send_message(
            message.chat.id,
            f"♻️ *{cliente}* renovado hasta {local_nueva}",
            parse_mode="Markdown",
            reply_markup=admin_menu()
        )

    @bot.message_handler(func=lambda m: m.text == '❌ Eliminar')
    def eliminar(message):
        bot.send_message(
            message.chat.id, "✏️ *Nombre del cliente* a eliminar:", parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, ejecutar_eliminacion)

    def ejecutar_eliminacion(message):
        cliente = message.text.strip()
        if delete_config(cliente):
            bot.send_message(message.chat.id, f"🗑️ *{cliente}* eliminado.", parse_mode="Markdown", reply_markup=admin_menu())
        else:
            bot.send_message(message.chat.id, "❌ No se pudo eliminar.", reply_markup=admin_menu())
