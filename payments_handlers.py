# payments_handlers.py

import os
import re
import json
from datetime import datetime
from telebot import TeleBot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove, Message, CallbackQuery
)

from config import ADMIN_ID, PLANS, CLIENTS_DIR
from generator import create_config
from utils import calcular_nuevo_vencimiento
from storage import load_json, save_json

# =========================
# Config de pagos
# =========================
# Para "Saldo": NO se pide número de confirmación; el saldo se envía a este número.
SALDO_NUMBER = "56246700"

# Para Transfermóvil (CUP): se paga a la tarjeta y LUEGO se solicita al cliente
# que envíe el "número de confirmación" del comprobante.
CUP_CARD = "9204 1299 7691 8161"

# Ruta del JSON global de configuraciones (mismo dir que usas para .conf/.png)
CONFIGS_FILE = os.path.join(CLIENTS_DIR, 'configuraciones.json')

# =========================
# Estado temporal de compras
# =========================
# Estructura:
# PENDIENTES[user_id] = {
#   'plan': <str>,
#   'metodo': 'saldo' | 'cup',
#   'receipt_file_id': <str|None>,
#   'confirmacion': <str|None>,
#   'first_name': <str|None>,
#   'username': <str|None>,
# }
PENDIENTES = {}

# =========================
# Helpers UI
# =========================
def _kb_planes() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for p in PLANS.keys():
        kb.add(KeyboardButton(p))
    kb.add(KeyboardButton('🔙 Cancelar'))
    return kb

def _kb_metodos() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton('💳 Saldo'), KeyboardButton('🏦 Transferencia CUP'))
    kb.add(KeyboardButton('🔙 Cancelar'))
    return kb

def _sanitize_name(s: str) -> str:
    # Nombre seguro para archivos
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', s)[:40] or 'cliente'

# =========================
# Registro de handlers
# =========================
def register_payments_handlers(bot: TeleBot):

    # -------------------------
    # /planes — inicio
    # -------------------------
    @bot.message_handler(commands=['planes'])
    def planes_cmd(message: Message):
        user_id = message.from_user.id
        PENDIENTES[user_id] = {
            'plan': None,
            'metodo': None,
            'receipt_file_id': None,
            'confirmacion': None,
            'first_name': message.from_user.first_name or '',
            'username': message.from_user.username or ''
        }
        texto = (
            "🗂 *Planes disponibles*\n\n"
            "• Free (5 horas)\n"
            "• 15 días\n"
            "• 30 días\n\n"
            "Elige un plan para continuar:"
        )
        bot.send_message(
            message.chat.id,
            texto,
            parse_mode="Markdown",
            reply_markup=_kb_planes()
        )

    # -------------------------
    # Selección de plan
    # -------------------------
    @bot.message_handler(func=lambda m: m.text in list(PLANS.keys()) + ['🔙 Cancelar'])
    def seleccionar_plan(message: Message):
        user_id = message.from_user.id

        if message.text == '🔙 Cancelar':
            PENDIENTES.pop(user_id, None)
            return bot.send_message(
                message.chat.id,
                "✅ Operación cancelada.",
                reply_markup=ReplyKeyboardRemove()
            )

        if user_id not in PENDIENTES:
            # flujo no iniciado
            PENDIENTES[user_id] = {
                'first_name': message.from_user.first_name or '',
                'username': message.from_user.username or ''
            }

        PENDIENTES[user_id]['plan'] = message.text
        PENDIENTES[user_id]['metodo'] = None
        PENDIENTES[user_id]['receipt_file_id'] = None
        PENDIENTES[user_id]['confirmacion'] = None

        texto = (
            "💰 *Selecciona un método de pago:*\n\n"
            "• 💳 Saldo\n"
            "• 🏦 Transferencia CUP (Transfermóvil)"
        )
        bot.send_message(
            message.chat.id,
            texto,
            parse_mode="Markdown",
            reply_markup=_kb_metodos()
        )

    # -------------------------
    # Selección de método de pago
    # -------------------------
    @bot.message_handler(func=lambda m: m.text in ['💳 Saldo', '🏦 Transferencia CUP'])
    def seleccionar_metodo(message: Message):
        user_id = message.from_user.id
        if user_id not in PENDIENTES or not PENDIENTES[user_id].get('plan'):
            return bot.send_message(message.chat.id, "Primero elige un plan con /planes.")

        metodo = 'saldo' if message.text == '💳 Saldo' else 'cup'
        PENDIENTES[user_id]['metodo'] = metodo

        if metodo == 'saldo':
            # SIN pedir número de confirmación
            texto_saldo = (
                "💳 *Pago por Saldo*\n\n"
                f"1) Envía saldo a: *{SALDO_NUMBER}*\n"
                "2) Envía aquí la *captura del comprobante*.\n\n"
                "🕒 El administrador revisará tu pago y, si todo está bien, recibirás tu archivo y QR automáticamente."
            )
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton(
                    "❌ Cancelar transacción",
                    callback_data=f"pago_cancelar:{user_id}"
                )
            )
            bot.send_message(
                message.chat.id,
                texto_saldo,
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            texto_cup = (
                "🏦 Transferencia CUP (Transfermóvil)\n\n"
                f"1) Envía CUP a la tarjeta: {CUP_CARD}.\n"
                "2) Envía aquí la captura del comprobante.\n"
                "3) Luego te pediré el número de confirmación de Transfermóvil.\n\n"
                "🕒 El administrador revisará tu pago y, si todo está bien, recibirás tu archivo y QR automáticamente."
            )
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton(
                    "❌ Cancelar transacción",
                    callback_data=f"pago_cancelar:{user_id}"
                )
            )
            bot.send_message(
                message.chat.id,
                texto_cup,
                reply_markup=markup
            )

    # -------------------------
    # Recibo (foto) del cliente
    # -------------------------
    @bot.message_handler(content_types=['photo'])
    def recibir_captura(message: Message):
        user_id = message.from_user.id
        if user_id not in PENDIENTES or not PENDIENTES[user_id].get('metodo'):
            return bot.send_message(message.chat.id, "Primero selecciona plan y método con /planes.")

        # Guardamos el file_id de la imagen de mayor resolución
        file_id = message.photo[-1].file_id
        PENDIENTES[user_id]['receipt_file_id'] = file_id

        if PENDIENTES[user_id]['metodo'] == 'cup':
            # pedir número de confirmación
            bot.send_message(
                message.chat.id,
                "🔢 Envía ahora el *número de confirmación* de Transfermóvil:",
                parse_mode="Markdown"
            )
            return

        # Para SALDO, podemos enviar al admin sin pedir confirmación
        _enviar_solicitud_al_admin(bot, message, require_confirm=False)

    # -------------------------
    # Número de confirmación (solo CUP)
    # -------------------------
    @bot.message_handler(
        func=lambda m: (
            m.from_user.id in PENDIENTES
            and PENDIENTES[m.from_user.id].get('metodo') == 'cup'
            and PENDIENTES[m.from_user.id].get('receipt_file_id') is not None
            and not PENDIENTES[m.from_user.id].get('confirmacion')
            and m.text is not None
        )
    )
    def recibir_confirmacion_cup(message: Message):
        user_id = message.from_user.id
        PENDIENTES[user_id]['confirmacion'] = message.text.strip()
        _enviar_solicitud_al_admin(bot, message, require_confirm=True)

    # -------------------------
    # Callbacks del admin (Aprobar / Rechazar) y Cancelar del cliente
    # -------------------------
    @bot.callback_query_handler(func=lambda c: c.data.startswith('pago_aprobar:') or c.data.startswith('pago_rechazar:') or c.data.startswith('pago_cancelar:'))
    def callbacks_pago(call: CallbackQuery):
        # Cancelación por parte del cliente (botón inline)
        if call.data.startswith('pago_cancelar:'):
            try:
                uid = int(call.data.split(':', 1)[1])
            except Exception:
                return bot.answer_callback_query(call.id, "ID inválido.")
            PENDIENTES.pop(uid, None)
            bot.answer_callback_query(call.id, "Operación cancelada.")
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            except Exception:
                pass
            bot.send_message(uid, "✅ Operación cancelada. Puedes volver a usar /planes cuando quieras.")
            return

        # Solo admin puede aprobar/rechazar
        if call.from_user.id != ADMIN_ID:
            return bot.answer_callback_query(call.id, "Sin permisos.")

        action, uid_str = call.data.split(':', 1)
        try:
            uid = int(uid_str)
        except ValueError:
            return bot.answer_callback_query(call.id, "ID inválido.")

        data = PENDIENTES.get(uid)
        if not data:
            return bot.answer_callback_query(call.id, "Solicitud no encontrada o ya procesada.")

        if action == 'pago_rechazar':
            bot.answer_callback_query(call.id, "Rechazado.")
            bot.send_message(uid, "❌ Tu pago fue *rechazado*. Revisa los datos e inténtalo otra vez.", parse_mode="Markdown")
            PENDIENTES.pop(uid, None)
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            except Exception:
                pass
            return

        # Aprobar
        plan = data['plan']
        venc = calcular_nuevo_vencimiento(plan)

        # Nombre del cliente (generado). Puedes cambiarlo si luego pides nombre explícito
        base_name = data.get('first_name') or data.get('username') or f"user{uid}"
        safe_name = _sanitize_name(f"{base_name}_{uid}_{datetime.now().strftime('%m%d%H%M')}")

        ok, conf_path, qr_path = create_config(safe_name, venc)
        if not ok:
            bot.answer_callback_query(call.id, "Error al crear config.")
            bot.send_message(uid, f"❌ Ocurrió un error al generar tu configuración:\n{conf_path}")
            PENDIENTES.pop(uid, None)
            return

        # Guardar/actualizar el plan en configuraciones.json para futuras renovaciones
        try:
            data_json = load_json(CONFIGS_FILE)
            if safe_name not in data_json:
                data_json[safe_name] = {}
            data_json[safe_name]['vencimiento'] = venc.strftime("%Y-%m-%d %H:%M")
            data_json[safe_name]['activa'] = True
            data_json[safe_name]['plan'] = plan
            save_json(CONFIGS_FILE, data_json)
        except Exception as e:
            # No interrumpimos el envío al usuario si falla esta parte
            print(f"[payments_handlers] No se pudo guardar plan en JSON: {e}")

        # Enviar al cliente
        caption = (
            f"✅ *Compra aprobada*\n"
            f"📦 Plan: *{plan}*\n"
            f"👤 Cliente: *{safe_name}*\n"
            f"📅 Vence: *{venc.strftime('%d/%m/%Y %I:%M %p')}*"
        )
        try:
            with open(conf_path, 'rb') as f:
                bot.send_document(uid, f, caption=caption, parse_mode="Markdown")
            if os.path.exists(qr_path):
                with open(qr_path, 'rb') as qrf:
                    bot.send_photo(uid, qrf, caption="📷 Escanéame para importar rápido.")
        except Exception as e:
            bot.send_message(uid, f"⚠️ Configuración creada pero no pude enviarte los archivos: {e}")

        bot.answer_callback_query(call.id, "Aprobado y enviado ✅")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
        PENDIENTES.pop(uid, None)


# =========================
# Enviar solicitud al admin con foto + botones
# =========================
def _enviar_solicitud_al_admin(bot: TeleBot, message: Message, require_confirm: bool):
    user_id = message.from_user.id
    data = PENDIENTES.get(user_id, {})
    if not data or not data.get('receipt_file_id'):
        return bot.send_message(message.chat.id, "Falta la captura del comprobante.")

    plan = data['plan']
    metodo = data['metodo']
    confirm_txt = data.get('confirmacion') if require_confirm else None

    texto = (
        f"📥 *Nueva solicitud de compra*\n"
        f"👤 Usuario: *{message.from_user.first_name or ''}* (ID: `{user_id}`)\n"
        f"📦 Plan: *{plan}*\n"
        f"💳 Método: *{'Saldo' if metodo=='saldo' else 'Transferencia CUP'}*\n"
    )
    if confirm_txt:
        texto += f"🔢 Confirmación TM: `{confirm_txt}`\n"

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Aprobar", callback_data=f"pago_aprobar:{user_id}"),
        InlineKeyboardButton("❌ Rechazar", callback_data=f"pago_rechazar:{user_id}")
    )

    # Enviar al admin
    try:
        bot.send_photo(
            ADMIN_ID,
            data['receipt_file_id'],
            caption=texto,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception as e:
        return bot.send_message(message.chat.id, f"❌ Error al enviar al admin: {e}")

    # Avisar al cliente
    bot.send_message(
        message.chat.id,
        "📨 Recibido. Tu pago está en *revisión*. Te avisamos pronto.",
        parse_mode="Markdown"
        )
