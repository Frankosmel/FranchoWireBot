# generator.py

import os
import subprocess
from datetime import datetime
from config import SCRIPT_PATH, CLIENTS_DIR
from utils import ruta_conf_cliente, generar_qr_desde_conf

def create_config(cliente: str, vencimiento: datetime):
    """
    Ejecuta el script de creación de cliente, devuelve una tupla:
    (success: bool, path_conf: str or error_msg: str, path_qr: str or None)
    """
    # Invocamos el script bash
    result = subprocess.run(
        ["sudo", "bash", SCRIPT_PATH, cliente],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        # error.stderr contiene el mensaje de fallo
        return False, result.stderr.strip(), None

    # Ubicaciones esperadas
    conf_path = os.path.join(CLIENTS_DIR, f"{cliente}.conf")
    qr_path   = os.path.join(CLIENTS_DIR, f"{cliente}.png")

    # Verificamos que existan
    if not os.path.isfile(conf_path):
        return False, f"No se encontró {conf_path}", None
    if not os.path.isfile(qr_path):
        # si quieres puedes generar el QR aquí mismo
        # qr = generar_qr_desde_conf(conf_path)
        # with open(qr_path, "wb") as f: f.write(qr.read())
        return False, f"No se encontró {qr_path}", None

    return True, conf_path, qr_path
