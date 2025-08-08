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

# =========================
# Config de pagos
# =========================
SALDO_NUMBER = "56246700"               # Enviar saldo a este número (NO pedir confirmación aquí)
CUP_CARD     = "9204 1299 7691 8161"    # Tarjeta CUP (Transfermóvil) — aquí SÍ pedimos # de confirmación

# JSON central de configs
CONFIGS_FILE = os.path.join(CLIENTS_DIR, 'configuraciones.json')

# =========================
# Estado temporal de compras
# =========================
# PENDIENTES[user_id] = {
#   'plan': <str>,
#   'metodo': 'saldo' | 'cup',
#   'receipt_file_id': <str|None>,
#   'confirmacion': <str|None>,
#   'user_first_name': <str|None>
# }
PENDIENTES = {}

# =========================
# Helpers de UI
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

def _inline_cancel(uid: int) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("🛑 Cancelar compra", callback_data=f"pago_cancelar:{uid}"))
    return m

def _sanitize_name(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', s)[:40] or 'cliente'

def _ensure_configs_json():
    folder = os.path.dirname(CONFIGS_FILE)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    if not os.path.isfile(CONFIGS_FILE):
        with open(CONFIGS_FILE, 'w') as f:
            json.dump({}, f, indent=2)

# =========================
# Registro de handlers
# =========================
def register_payments_handlers(bot: TeleBot):

    # /planes — inicio
    @bot.message_handler(commands=['planes'])
    def planes_cmd(message: Message):
        user_id = message.from_user.id
        PENDIENTES.pop(user_id, None)  # limpiar cualquier estado anterior
        PENDIENTES[user_id] = {'user_first_name': message.from_user.first_name or ''}
        bot.send_message(
            message.chat.id,
            "🗂 *Planes disponibles*\n\n"
            "🔹 Free (5 horas)\n"
            "🔹 15 días\n"
            "🔹 30 días\n\n"
            "👉 Elige un plan para continuar:",
            parse_mode="Markdown",
            reply_markup=_kb_planes()
        )
        # botón inline de cancelación
        bot.send_message(message.chat.id, "Si cambiaste de idea, puedes cancelar aquí:", reply_markup=_inline_cancel(user_id))

    # Selección de plan
    @bot.message_handler(func=lambda m: m.text in list(PLANS.keys()) + ['🔙 Cancelar'])
    def seleccionar_plan(message: Message):
        user_id = message.from_user.id

        if message.text == '🔙 Cancelar':
            PENDIENTES.pop(user_id, None)
            return bot.send_message(message.chat.id, "✅ Operación cancelada.", reply_markup=ReplyKeyboardRemove())

        if user_id not in PENDIENTES:
            PENDIENTES[user_id] = {}
        PENDIENTES[user_id]['plan'] = message.text
        PENDIENTES[user_id]['metodo'] = None
        PENDIENTES[user_id]['receipt_file_id'] = None
        PENDIENTES[user_id]['confirmacion'] = None
        PENDIENTES[user_id]['user_first_name'] = message.from_user.first_name or PENDIENTES[user_id].get('user_first_name', '')

        bot.send_message(
            message.chat.id,
            "💳 *Selecciona un método de pago:*\n\n"
            "• 💳 *Saldo* → Envía saldo al número indicado y luego manda la *captura* aquí.\n"
            "• 🏦 *Transferencia CUP* → Envía a la tarjeta y luego manda *captura* + *número de confirmación*.",
            parse_mode="Markdown",
            reply_markup=_kb_metodos()
        )
        bot.send_message(message.chat.id, "Puedes cancelar en cualquier momento:", reply_markup=_inline_cancel(user_id))

    # Selección de método
    @bot.message_handler(func=lambda m: m.text in ['💳 Saldo', '🏦 Transferencia CUP'])
    def seleccionar_metodo(message: Message):
        user_id = message.from_user.id
        if user_id not in PENDIENTES or not PENDIENTES[user_id].get('plan'):
            return bot.send_message(message.chat.id, "Primero elige un plan con /planes.")

        metodo = 'saldo' if message.text == '💳 Saldo' else 'cup'
        PENDIENTES[user_id]['metodo'] = metodo

        if metodo == 'saldo':
            bot.send_message(
                message.chat.id,
                f"💳 *Pago por Saldo*\n\n"
                f"1) Envía saldo a: *{SALDO_NUMBER}*.\n"
                f"2) Envía aquí la *captura del comprobante*.\n\n"
                f"🕒 El administrador revisará tu pago y, si todo está bien, recibirás tu archivo y QR automáticamente.",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            bot.send_message(
                message.chat.id,
                f"🏦 *Transferencia CUP (Transfermóvil)*\n\n"
                f"1) Envía CUP a la tarjeta: *{CUP_CARD}*.\n"
                f"2) Envía aquí la *captura del comprobante*.\n"
                f"3) Luego te pediré el *número de confirmación* de Transfermóvil.\n\n"
                f"🕒 El administrador revisará tu pago y, si todo está bien, recibirás tu archivo y QR automáticamente.",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
        bot.send_message(message.chat.id, "Si te equivocaste, cancela aquí:", reply_markup=_inline_cancel(user_id))

    # Recibir captura
    @bot.message_handler(content_types=['photo'])
    def recibir_captura(message: Message):
        user_id = message.from_user.id
        if user_id not in PENDIENTES or not PENDIENTES[user_id].get('metodo'):
            return bot.send_message(message.chat.id, "Primero selecciona plan y método con /planes.")

        file_id = message.photo[-1].file_id
        PENDIENTES[user_id]['receipt_file_id'] = file_id

        if PENDIENTES[user_id]['metodo'] == 'cup':
            # pedir confirmación TM
            return bot.send_message(
                message.chat.id,
                "🔢 Envía ahora el *número de confirmación* de Transfermóvil:",
                parse_mode="Markdown",
                reply_markup=_inline_cancel(user_id)
            )

        # SALDO: enviar al admin directo
        _enviar_solicitud_al_admin(bot, message, require_confirm=False)

    # Número de confirmación (solo CUP)
    @bot.message_handler(func=lambda m: (
        m.text
        and m.from_user.id in PENDIENTES
        and PENDIENTES[m.from_user.id].get('metodo') == 'cup'
        and PENDIENTES[m.from_user.id].get('receipt_file_id')
        and not PENDIENTES[m.from_user.id].get('confirmacion')
    ))
    def recibir_confirmacion_cup(message: Message):
        user_id = message.from_user.id
        PENDIENTES[user_id]['confirmacion'] = message.text.strip()
        _enviar_solicitud_al_admin(bot, message, require_confirm=True)

    # Cancelación por inline button
    @bot.callback_query_handler(func=lambda c: c.data.startswith('pago_cancelar:'))
    def cancelar_cb(call: CallbackQuery):
        try:
            uid = int(call.data.split(':', 1)[1])
        except ValueError:
            return bot.answer_callback_query(call.id, "ID inválido.")

        if call.from_user.id != uid:
            return bot.answer_callback_query(call.id, "No puedes cancelar esta compra.")

        PENDIENTES.pop(uid, None)
        bot.answer_callback_query(call.id, "Compra cancelada.")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(uid, "🛑 Compra cancelada. Puedes comenzar de nuevo con /planes.")

    # Admin: Aprobar / Rechazar
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
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            except Exception:
                pass
            return

        # === Aprobar ===
        plan = data['plan']
        venc = calcular_nuevo_vencimiento(plan)
        buyer_name = data.get('user_first_name') or 'user'
        safe_name = _sanitize_name(f"{buyer_name}_{uid}_{datetime.now().strftime('%m%d%H%M')}")

        ok, conf_path, qr_path = create_config(safe_name, venc)
        if not ok:
            bot.answer_callback_query(call.id, "Error al crear config.")
            bot.send_message(uid, f"❌ Ocurrió un error al generar tu configuración:\n`{conf_path}`", parse_mode="Markdown")
            PENDIENTES.pop(uid, None)
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            except Exception:
                pass
            return

        # Guardar el plan en configuraciones.json para que RENOVAR funcione
        try:
            _ensure_configs_json()
            with open(CONFIGS_FILE, 'r') as f:
                existing = json.load(f)
        except Exception:
            existing = {}
        if safe_name not in existing:
            existing[safe_name] = {}
        existing[safe_name]['plan'] = plan
        existing[safe_name]['vencimiento'] = venc.strftime("%Y-%m-%d %H:%M")
        existing[safe_name]['activa'] = True
        try:
            with open(CONFIGS_FILE, 'w') as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            # No es crítico para entregar el archivo
            bot.send_message(ADMIN_ID, f"⚠️ No pude actualizar configuraciones.json: {e}")

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
        except Exception as e:
            bot.send_message(uid, f"⚠️ No pude adjuntar el archivo .conf automáticamente: `{e}`", parse_mode="Markdown")

        if os.path.exists(qr_path):
            try:
                with open(qr_path, 'rb') as qrf:
                    bot.send_photo(uid, qrf, caption="📷 Escanéame para importar rápido.")
            except Exception as e:
                bot.send_message(uid, f"⚠️ No pude enviar el QR: `{e}`", parse_mode="Markdown")
        else:
            bot.send_message(uid, "⚠️ No se pudo generar el QR. Aún puedes importar el `.conf` manualmente.\n"
                                  "Sugerencia al admin: instala `Pillow` en el entorno.", parse_mode="Markdown")

        bot.answer_callback_query(call.id, "Aprobado y enviado ✅")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
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
        bot.send_photo(
            ADMIN_ID,
            data['receipt_file_id'],
            caption=texto,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception as e:
        return bot.send_message(message.chat.id, f"❌ Error al enviar al admin: {e}")

    bot.send_message(
        message.chat.id,
        "📨 Recibido. Tu pago está en *revisión*. Te avisamos pronto.",
        parse_mode="Markdown"
        )
