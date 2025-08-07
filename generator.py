# generator.py  ✅ Corregido para usar la MISMA ruta de JSON y la
#                función registrar_config de utils.py

import os
import subprocess
from datetime import datetime

from config import SCRIPT_PATH, CLIENTS_DIR
from utils import (
    ruta_conf_cliente,
    ruta_qr_cliente,
    generate_qr,
    registrar_config          # ← nuevo: guardamos todo en un solo sitio
)

def create_config(cliente: str, plan: str, vencimiento: datetime):
    """
    Crea una nueva configuración WireGuard:

    • Ejecuta el script bash (SCRIPT_PATH) → genera .conf
    • Genera el QR si falta.
    • Registra la entrada en *data/configuraciones.json* mediante utils.registrar_config

    Retorna:
        (True, ruta_conf, ruta_qr)    en éxito
        (False, mensaje_error, None)  en error
    """

    # 1️⃣  Ejecutar el script bash
    result = subprocess.run(
        ["sudo", "bash", SCRIPT_PATH, cliente],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return False, result.stderr.strip(), None

    # 2️⃣  Verificar rutas generadas
    conf_path = ruta_conf_cliente(cliente)
    qr_path   = ruta_qr_cliente(cliente)

    if not os.path.isfile(conf_path):
        return False, f"No se encontró {conf_path}", None

    # 3️⃣  Generar QR si aún no existe
    if not os.path.isfile(qr_path):
        try:
            generate_qr(conf_path)
        except Exception as e:
            return False, f"Error al generar QR: {e}", None

    # 4️⃣  Registrar en configuraciones.json (una sola fuente de verdad)
    registrar_config(cliente, plan, vencimiento)

    return True, conf_path, qr_path
