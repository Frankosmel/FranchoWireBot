# admin_handlers.py

import os
from datetime import datetime
from zoneinfo import ZoneInfo  # ⬅️ usamos zona horaria sin dependencias externas
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from config import ADMIN_ID, PLANS, CLIENTS_DIR
from storage import load_json, save_json
from utils import generate_qr, delete_config, get_stats, calcular_nuevo_vencimiento
from generator import create_config

CONFIGS_FILE = os.path.join(CLIENTS_DIR, 'configuraciones.json')

# ====== ZONAS HORARIAS ======
TZ_UTC = ZoneInfo("UTC")
TZ_CUBA = ZoneInfo("America/Havana")

def _parse_dt_any_utc(s: str) -> datetime:
    """Parsea string del JSON y lo devuelve con tz UTC."""
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=TZ_UTC)
        except ValueError:
            pass
    # si nada funcionó, re-lanza con el formato base
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=TZ_UTC)

def _fmt_cuba_from_str(s: str) -> str:
    """Convierte string UTC del JSON a string hora Cuba 12h."""
    return _parse_dt_any_utc(s).astimezone(TZ_CUBA).strftime("%d/%m/%Y %I:%M %p")

def _fmt_cuba_from_dt(dt: datetime) -> str:
    """Convierte datetime (asumido UTC naive) a string hora Cuba 12h."""
    return dt.replace(tzinfo=TZ_UTC).astimezone(TZ_CUBA).strftime("%d/%m/%Y %I:%M %p")

# ====== MENÚS ======
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
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=admin_menu())

    @bot.message_handler(func=lambda m: m.text == '🔙 Volver')
    def back_to_main(message):
        bot.send_message(message.chat.id, "↩️ Menú principal.", reply_markup=admin_menu())

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

    # ===== CREAR =====
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
            return bot.send_message(message.chat.id, "↩️ Menú principal.", reply_markup=admin_menu())

        data = TEMP.get(message.chat.id, {})
        cliente = data.get('cliente')
        plan = message.text

        if not cliente:
            return bot.send_message(message.chat.id, "❌ Nombre inválido.", reply_markup=admin_menu())
        if plan not in PLANS:
            return bot.send_message(message.chat.id, "❌ Plan inválido, intenta de nuevo.", reply_markup=admin_menu())

        venc = calcular_nuevo_vencimiento(plan)
        success, conf_path, qr_path = create_config(cliente, plan, venc)
        if not success:
            return bot.send_message(message.chat.id, f"❌ Error: {conf_path}", reply_markup=admin_menu())

        # Guardar/actualizar en JSON con plan
        datos = load_json(CONFIGS_FILE)
        datos[cliente] = {
            "plan": plan,
            "vencimiento": venc.strftime("%Y-%m-%d %H:%M"),  # UTC en JSON
            "activa": True
        }
        save_json(CONFIGS_FILE, datos)

        caption = (
            f"✅ *{cliente}* creado.\n"
            f"📅 Vence el: *{_fmt_cuba_from_dt(venc)}* (hora Cuba)"
        )
        if os.path.exists(conf_path):
            with open(conf_path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=caption, parse_mode="Markdown")
        if os.path.exists(qr_path):
            with open(qr_path, 'rb') as qr:
                bot.send_photo(message.chat.id, qr)

        TEMP.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "↩️ Menú principal.", reply_markup=admin_menu())

    # ===== VER TODAS =====
    @bot.message_handler(func=lambda m: m.text == '🗂 Ver todas')
    def ver_todas(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "ℹ️ No hay configuraciones.")
        lines = ["📁 *Configuraciones registradas:*"]
        for cli, info in datos.items():
            estado = "✅ Activa" if info.get('activa') else "⛔️ Expirada"
            venc_s = info.get('vencimiento', '—')
            plan_s = info.get('plan', '—')
            try:
                venc_local = _fmt_cuba_from_str(venc_s)
            except Exception:
                venc_local = venc_s
            lines.append(f"• {cli}: {estado} — vence {venc_local} — plan {plan_s}")
        bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")

    # ===== POR EXPIRAR =====
    @bot.message_handler(func=lambda m: m.text == '📆 Por expirar')
    def por_expirar(message):
        datos = load_json(CONFIGS_FILE)
        proximas = []
        ahora_utc = datetime.now(TZ_UTC)
        for cli, info in datos.items():
            venc_s = info.get('vencimiento')
            if not venc_s:
                continue
            try:
                vendt_utc = _parse_dt_any_utc(venc_s)
            except Exception:
                continue
            dias = (vendt_utc - ahora_utc).days
            if 0 <= dias <= 3:
                proximas.append((cli, dias, vendt_utc))
        if not proximas:
            return bot.send_message(message.chat.id, "✅ No hay configuraciones próximas a expirar.")
        lines = ["📆 *Por expirar en próximos 3 días:*"]
        for cli, dias, vendt_utc in proximas:
            lines.append(f"• {cli}: vence en {dias} día(s) — {_fmt_cuba_from_str(vendt_utc.strftime('%Y-%m-%d %H:%M'))}")
        bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")

    # ===== RENOVAR =====
    @bot.message_handler(func=lambda m: m.text == '♻️ Renovar')
    def renew_menu(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "ℹ️ No hay configuraciones para renovar.", reply_markup=admin_menu())
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for cli in sorted(datos.keys()):
            kb.add(KeyboardButton(cli))
        kb.add(KeyboardButton('🔙 Menú admin'))
        TEMP[message.chat.id] = {'accion': 'renovar'}
        bot.send_message(message.chat.id, "♻️ Selecciona un cliente a renovar:", reply_markup=kb)
        bot.register_next_step_handler(message, _renovar_elegir_plan)

    def _renovar_elegir_plan(message):
        if message.text == '🔙 Menú admin':
            TEMP.pop(message.chat.id, None)
            return bot.send_message(message.chat.id, "↩️ Menú principal.", reply_markup=admin_menu())

        cliente = message.text.strip()
        datos = load_json(CONFIGS_FILE)
        if cliente not in datos:
            return bot.send_message(message.chat.id, "❌ Cliente no encontrado.", reply_markup=admin_menu())

        TEMP[message.chat.id] = {'accion': 'renovar', 'cliente': cliente}
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for plan in PLANS:
            kb.add(KeyboardButton(plan))
        kb.add(KeyboardButton('🔙 Menú admin'))
        bot.send_message(message.chat.id, f"🗓 *Plan para renovar {cliente}:*", parse_mode="Markdown", reply_markup=kb)
        bot.register_next_step_handler(message, _renovar_aplicar)

    def _renovar_aplicar(message):
        if message.text == '🔙 Menú admin':
            TEMP.pop(message.chat.id, None)
            return bot.send_message(message.chat.id, "↩️ Menú principal.", reply_markup=admin_menu())

        data = TEMP.get(message.chat.id, {})
        cliente = data.get('cliente')
        plan = message.text

        if plan not in PLANS or not cliente:
            TEMP.pop(message.chat.id, None)
            return bot.send_message(message.chat.id, "❌ Datos inválidos.", reply_markup=admin_menu())

        datos = load_json(CONFIGS_FILE)
        if cliente not in datos:
            TEMP.pop(message.chat.id, None)
            return bot.send_message(message.chat.id, "❌ Cliente no encontrado.", reply_markup=admin_menu())

        nuevo_venc = calcular_nuevo_vencimiento(plan)
        datos[cliente]['vencimiento'] = nuevo_venc.strftime("%Y-%m-%d %H:%M")  # UTC en JSON
        datos[cliente]['plan'] = plan
        datos[cliente]['activa'] = True
        save_json(CONFIGS_FILE, datos)

        TEMP.pop(message.chat.id, None)
        bot.send_message(
            message.chat.id,
            f"♻️ *{cliente}* renovado hasta {_fmt_cuba_from_dt(nuevo_venc)} (plan: {plan})",
            parse_mode="Markdown",
            reply_markup=admin_menu()
        )

    # ===== ELIMINAR =====
    @bot.message_handler(func=lambda m: m.text == '❌ Eliminar')
    def delete_menu(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "ℹ️ No hay configuraciones para eliminar.", reply_markup=admin_menu())
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for cli in sorted(datos.keys()):
            kb.add(KeyboardButton(cli))
        kb.add(KeyboardButton('🔙 Menú admin'))
        bot.send_message(message.chat.id, "❌ Selecciona un cliente a eliminar:", reply_markup=kb)
        bot.register_next_step_handler(message, ejecutar_eliminacion)

    def ejecutar_eliminacion(message):
        if message.text == '🔙 Menú admin':
            return bot.send_message(message.chat.id, "↩️ Menú principal.", reply_markup=admin_menu())
        cliente = message.text.strip()
        if delete_config(cliente):
            datos = load_json(CONFIGS_FILE)
            if cliente in datos:
                datos.pop(cliente)
                save_json(CONFIGS_FILE, datos)
            bot.send_message(message.chat.id, f"🗑️ *{cliente}* eliminado.", parse_mode="Markdown", reply_markup=admin_menu())
        else:
            bot.send_message(message.chat.id, "❌ No se encontró el cliente.", reply_markup=admin_menu())

    # ===== VER QR =====
    @bot.message_handler(func=lambda m: m.text == '📁 Ver QR')
    def qr_menu(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "ℹ️ No hay configuraciones.", reply_markup=admin_menu())
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for cli in sorted(datos.keys()):
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

    # ===== DESCARGAR .CONF =====
    @bot.message_handler(func=lambda m: m.text == '📄 Descargar .conf')
    def conf_menu(message):
        datos = load_json(CONFIGS_FILE)
        if not datos:
            return bot.send_message(message.chat.id, "ℹ️ No hay configuraciones.", reply_markup=admin_menu())
        kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for cli in sorted(datos.keys()):
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
