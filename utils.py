# utils.py

import os
import json
import qrcode
from datetime import datetime, timedelta

from config import (
    WG_CONFIG_DIR,
    CLIENTS_DIR,
    PLANS
)

# Ruta donde guardamos el JSON con metadatos de todos los clientes
CONFIGS_FILE = os.path.join(CLIENTS_DIR, 'configuraciones.json')

# ========================= RUTAS =========================

def ruta_conf_cliente(nombre: str) -> str:
    """Devuelve la ruta absoluta del .conf de un cliente."""
    return os.path.join(CLIENTS_DIR, f"{nombre}.conf")

def ruta_qr_cliente(nombre: str) -> str:
    """Devuelve la ruta absoluta del .png QR de un cliente."""
    return os.path.join(CLIENTS_DIR, f"{nombre}.png")


# ========================= VENCIMIENTOS =========================

def calcular_nuevo_vencimiento(plan: str) -> datetime:
    """
    Calcula la nueva fecha de vencimiento según el plan elegido.
    Planes definidos en config.PLANS con claves 'dias' o 'horas'.
    """
    delta = PLANS.get(plan, {})
    dias = delta.get('dias', 0)
    horas = delta.get('horas', 0)
    return datetime.now() + timedelta(days=dias, hours=horas)


# ========================= QR =========================

def generate_qr(ruta_conf: str) -> str:
    """
    Genera un PNG con código QR a partir del contenido de un .conf.
    Devuelve la ruta al .png generado.
    """
    if not os.path.exists(ruta_conf):
        raise FileNotFoundError(f"No existe el archivo de configuración: {ruta_conf}")
    with open(ruta_conf, 'r') as f:
        contenido = f.read()
    img = qrcode.make(contenido)
    qr_path = ruta_qr_cliente(os.path.splitext(os.path.basename(ruta_conf))[0])
    img.save(qr_path)
    return qr_path


# ========================= ESTADÍSTICAS =========================

def get_stats() -> (int, int):
    """
    Retorna una tupla (activos, expirados) según las fechas en CONFIGS_FILE.
    Si no existe el JSON, devuelve (0,0).
    """
    if not os.path.exists(CONFIGS_FILE):
        return 0, 0
    with open(CONFIGS_FILE, 'r') as f:
        data = json.load(f)
    activos = expirados = 0
    ahora = datetime.now()
    for info in data.values():
        venc = datetime.strptime(info['vencimiento'], "%Y-%m-%d %H:%M")
        if venc > ahora:
            activos += 1
        else:
            expirados += 1
    return activos, expirados


# ========================= RENOVACIÓN =========================

def renew_config(nombre: str) -> (bool, datetime):
    """
    Renueva la fecha de vencimiento de un cliente.
    Retorna (True, nueva_fecha) si existía, o (False, None) en otro caso.
    """
    if not os.path.exists(CONFIGS_FILE):
        return False, None
    with open(CONFIGS_FILE, 'r') as f:
        data = json.load(f)
    if nombre not in data:
        return False, None
    nueva_fecha = calcular_nuevo_vencimiento(data[nombre]['plan'])
    data[nombre]['vencimiento'] = nueva_fecha.strftime("%Y-%m-%d %H:%M")
    with open(CONFIGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    return True, nueva_fecha


# ========================= ELIMINACIÓN =========================

def delete_config(nombre: str) -> bool:
    """
    Elimina .conf, .png y la entrada JSON de CONFIGS_FILE.
    Retorna True si algo se borró, False si no encontró nada.
    """
    removed = False

    # Borrar .conf
    conf = ruta_conf_cliente(nombre)
    if os.path.exists(conf):
        os.remove(conf)
        removed = True

    # Borrar QR
    qr = ruta_qr_cliente(nombre)
    if os.path.exists(qr):
        os.remove(qr)
        removed = True

    # Borrar del JSON
    if os.path.exists(CONFIGS_FILE):
        with open(CONFIGS_FILE, 'r') as f:
            data = json.load(f)
        if nombre in data:
            data.pop(nombre)
            with open(CONFIGS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            removed = True

    return removed
