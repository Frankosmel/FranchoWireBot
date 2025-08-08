# payments_handlers.py

import os
import re
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

# =========================
# Config de pagos
# =========================
SALDO_NUMBER = "56246700"                      # Enviar saldo a este número (no pedir confirmación)
CUP_CARD     = "9204 1299 7691 8161"          # Tarjeta CUP
# NOTA: para Transfermóvil (CUP) SÍ pedimos "número de confirmación" después de la captura

# =========================
# Estado temporal de compras
# =========================
# Estructura:
# PENDIENTES[user_id] = {
#   'plan': <str>,
#   'metodo': 'saldo' | 'cup',
#   'receipt_file_id': <str|None>,
#   'confirmacion': <str|None>,
# }
PENDIENTES = {}

# Helpers
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
    # nombre de cliente seguro para archivo
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', s)[:40] or 'cliente'

def register_payments_handlers(bot: TeleBot):

    # =========================
    # /planes — inicio del flujo de compra
    # =========================
    @bot.message_handler(commands=['planes'])
    def planes_cmd(message: Message):
        user_id = message.from_user.id
        PENDIENTES.pop(user_id, None)  # limpiar cualquier estado anterior
        bot.send_message(
            message.chat.id,
            "🗂 *Planes disponibles*\n\n"
            "• Free (5 horas)\n"
            "• 15 días\n"
            "• 30 días\n\n"
            "Elige un plan:",
            parse_mode="Markdown",
            reply_markup=_kb_planes()
        )

    # =========================
    # Selección de plan
    # =========================
    @bot.message_handler(func=lambda m: m.text in list(PLANS.keys()) + ['🔙 Cancelar'])
    def seleccionar_plan(message: Message):
        if message.text == '🔙 Cancelar':
            PENDIENTES.pop(message.from_user.id, None)
            return bot.send_message(message.chat.id, "✅ Operación cancelada.", reply_markup=ReplyKeyboardRemove())

        user_id = message.from_user.id
        PENDIENTES[user_id] = {
            'plan': message.text,
            'metodo': None,
            'receipt_file_id': None,
            'confirmacion': None
        }
        bot.send_message(
            message.chat.id,
            "💰 *Selecciona un método de pago:*",
            parse_mode="Markdown",
            reply_markup=_kb_metodos()
        )

    # =========================
    # Selección de método de pago
    # =========================
    @bot.message_handler(func=lambda m: m.text in ['💳 Saldo', '🏦 Transferencia CUP'])
    def seleccionar_metodo(message: Message):
        user_id = message.from_user.id
        if user_id not in PENDIENTES or not PENDIENTES[user_id].get('plan'):
            return bot.send_message(message.chat.id, "Primero elige un plan con /planes.")

        metodo = 'saldo' if message.text == '💳 Saldo' else 'cup'
        PENDIENTES[user_id]['metodo'] = metodo

        if metodo == 'saldo':
            # NO pedir número de confirmación aquí
            bot.send_message(
                message.chat.id,
                f"💳 *Pago por Saldo*\n\n"
                f"1) Envía saldo a: *{SALDO_NUMBER}*\n"
                f"2) Envía aquí la *captura del comprobante*.\n\n"
                f"Cuando la capture sea revisada y aprobada por el administrador, recibirás tu archivo y QR.",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            bot.send_message(
                message.chat.id,
                f"🏦 *Transferencia CUP*\n\n"
                f"1) Envía CUP a la tarjeta:\n*{CUP_CARD}*\n"
                f"2) Envía aquí la *captura del comprobante*.\n"
                f"3) Luego te pediré el *número de confirmación* de Transfermóvil.\n\n"
                f"Cuando el admin apruebe, recibirás tu archivo y QR.",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )

    # =========================
    # Recibo (foto) del cliente
    # =========================
    @bot.message_handler(content_types=['photo'])
    def recibir_captura(message: Message):
        user_id = message.from_user.id
        if user_id not in PENDIENTES or not PENDIENTES[user_id].get('metodo'):
            return bot.send_message(message.chat.id, "Primero selecciona plan y método con /planes.")

        file_id = message.photo[-1].file_id
        PENDIENTES[user_id]['receipt_file_id'] = file_id

        if PENDIENTES[user_id]['metodo'] == 'cup':
            # pedir número de confirmación
            bot.send_message(
                message.chat.id,
                "🔢 Envía ahora el *número de confirmación* de Transfermóvil:",
                parse_mode="Markdown"
            )
            # el próximo mensaje de texto se toma como confirmación
            return

        # Para SALDO, ya podemos enviar al admin sin pedir confirmación
        _enviar_solicitud_al_admin(bot, message, require_confirm=False)

    # =========================
    # Número de confirmación (solo CUP)
    # =========================
    @bot.message_handler(func=lambda m: m.text and m.from_user.id in PENDIENTES and PENDIENTES[m.from_user.id].get('metodo') == 'cup' and PENDIENTES[m.from_user.id].get('receipt_file_id') and not PENDIENTES[m.from_user.id].get('confirmacion'))
    def recibir_confirmacion_cup(message: Message):
        user_id = message.from_user.id
        PENDIENTES[user_id]['confirmacion'] = message.text.strip()
        _enviar_solicitud_al_admin(bot, message, require_confirm=True)

    # =========================
    # Callbacks del admin (Aprobar / Rechazar)
    # =========================
    @bot.callback_query_handler(func=lambda c: c.data.startswith('pago_aprobar:') or c.data.startswith('pago_rechazar:'))
    def callbacks_pago(call: CallbackQuery):
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
            return

        # Aprobar
        plan = data['plan']
        venc = calcular_nuevo_vencimiento(plan)

        # nombre de cliente: user_<id>_<fecha>
        # (puedes cambiar esto por un input previo si lo prefieres)
        safe_name = _sanitize_name(f"{call.from_user.first_name or 'user'}_{uid}_{datetime.now().strftime('%m%d%H%M')}")
        ok, conf_path, qr_path = create_config(safe_name, venc)
        if not ok:
            bot.answer_callback_query(call.id, "Error al crear config.")
            bot.send_message(uid, f"❌ Ocurrió un error al generar tu configuración:\n{conf_path}")
            PENDIENTES.pop(uid, None)
            return

        # Enviar al cliente
        caption = (
            f"✅ *Compra aprobada*\n"
            f"📦 Plan: *{plan}*\n"
            f"👤 Cliente: *{safe_name}*\n"
            f"📅 Vence: *{venc.strftime('%d/%m/%Y %I:%M %p')}*"
        )
        with open(conf_path, 'rb') as f:
            bot.send_document(uid, f, caption=caption, parse_mode="Markdown")
        if os.path.exists(qr_path):
            with open(qr_path, 'rb') as qrf:
                bot.send_photo(uid, qrf, caption="📷 Escanéame para importar rápido.")

        bot.answer_callback_query(call.id, "Aprobado y enviado ✅")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        PENDIENTES.pop(uid, None)

# =========================
# Enviar solicitud al admin
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

    try:
        # enviar al admin
        bot.send_photo(
            ADMIN_ID,
            data['receipt_file_id'],
            caption=texto,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception as e:
        return bot.send_message(message.chat.id, f"❌ Error al enviar al admin: {e}")

    bot.send_message(message.chat.id, "📨 Recibido. Tu pago está en *revisión*. Te avisamos pronto.", parse_mode="Markdown")
