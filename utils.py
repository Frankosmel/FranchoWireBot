# utils.py  ✅ Revisado y alineado con admin_handlers.py

import os
import json
import qrcode
from datetime import datetime, timedelta

from config import CLIENTS_DIR, PLANS

# 👉  La ruta debe ser la MISMA que usa admin_handlers.py
DATA_DIR = os.path.join(CLIENTS_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)                           # crea data/ si no existe
CONFIGS_FILE = os.path.join(DATA_DIR, "configuraciones.json")  # data/configuraciones.json


# ========================= RUTAS =========================
def ruta_conf_cliente(nombre: str) -> str:
    """Ruta absoluta del .conf de un cliente."""
    return os.path.join(CLIENTS_DIR, f"{nombre}.conf")


def ruta_qr_cliente(nombre: str) -> str:
    """Ruta absoluta del .png QR de un cliente."""
    return os.path.join(CLIENTS_DIR, f"{nombre}.png")


# ========================= ALTA / BAJA EN JSON =========================
def _leer_configs():
    if not os.path.exists(CONFIGS_FILE):
        return {}
    with open(CONFIGS_FILE, "r") as f:
        return json.load(f)


def _guardar_configs(data: dict):
    with open(CONFIGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def registrar_config(cliente: str, plan: str, vencimiento: datetime):
    """
    Guarda (o actualiza) la entrada de *cliente* en configuraciones.json
    """
    data = _leer_configs()
    data[cliente] = {
        "plan": plan,
        "vencimiento": vencimiento.strftime("%Y-%m-%d %H:%M"),
        "activa": True
    }
    _guardar_configs(data)


# ========================= VENCIMIENTOS =========================
def calcular_nuevo_vencimiento(plan: str) -> datetime:
    """Calcula la fecha de vencimiento según PLANS."""
    delta = PLANS.get(plan, {})
    return datetime.now() + timedelta(days=delta.get("dias", 0),
                                      hours=delta.get("horas", 0))


# ========================= QR =========================
def generate_qr(ruta_conf: str) -> str:
    """Genera y guarda un QR a partir de un .conf; devuelve la ruta del .png."""
    if not os.path.exists(ruta_conf):
        raise FileNotFoundError(f"No existe {ruta_conf}")
    with open(ruta_conf, "r") as f:
        contenido = f.read()

    img = qrcode.make(contenido)
    qr_path = ruta_qr_cliente(os.path.splitext(os.path.basename(ruta_conf))[0])
    img.save(qr_path)
    return qr_path


# ========================= ESTADÍSTICAS =========================
def get_stats() -> tuple[int, int]:
    """Devuelve (activos, expirados) a la fecha actual."""
    data = _leer_configs()
    ahora = datetime.now()
    activos = sum(datetime.strptime(v["vencimiento"], "%Y-%m-%d %H:%M") > ahora
                  for v in data.values())
    expirados = len(data) - activos
    return activos, expirados


# ========================= RENOVACIÓN =========================
def renew_config(nombre: str) -> tuple[bool, datetime | None]:
    """Renueva la config de *nombre* (mismo plan) y devuelve (ok, nueva_fecha)."""
    data = _leer_configs()
    if nombre not in data:
        return False, None

    plan = data[nombre]["plan"]
    nueva_fecha = calcular_nuevo_vencimiento(plan)
    data[nombre]["vencimiento"] = nueva_fecha.strftime("%Y-%m-%d %H:%M")
    _guardar_configs(data)
    return True, nueva_fecha


# ========================= ELIMINACIÓN =========================
def delete_config(nombre: str) -> bool:
    """Elimina archivos y entrada JSON; True si algo se borró."""
    removed = False

    # Archivos
    for path in (ruta_conf_cliente(nombre), ruta_qr_cliente(nombre)):
        if os.path.exists(path):
            os.remove(path)
            removed = True

    # JSON
    data = _leer_configs()
    if nombre in data:
        data.pop(nombre)
        _guardar_configs(data)
        removed = True

    return removed
