# generator.py

import os
import subprocess
import json
from datetime import datetime
from config import SCRIPT_PATH, CLIENTS_DIR
from utils import ruta_conf_cliente, ruta_qr_cliente, generate_qr

# Ruta al JSON que guarda metadatos de todas las configuraciones
CONFIGS_FILE = os.path.join(CLIENTS_DIR, 'configuraciones.json')

def create_config(cliente: str, vencimiento: datetime):
    """
    Ejecuta el script de creación de cliente, genera el .conf y el .png, 
    registra la nueva configuración en configuraciones.json, y devuelve:
      (True, ruta_conf, ruta_qr)
    o en caso de error:
      (False, mensaje_error, None)
    """
    # 1️⃣ Ejecutar el script bash
    result = subprocess.run(
        ["sudo", "bash", SCRIPT_PATH, cliente],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return False, result.stderr.strip(), None

    # 2️⃣ Rutas esperadas
    conf_path = ruta_conf_cliente(cliente)
    qr_path   = ruta_qr_cliente(cliente)

    # 3️⃣ Generar QR si no existe
    if not os.path.isfile(qr_path):
        try:
            generate_qr(conf_path)
        except Exception as e:
            return False, f"Error al generar QR: {e}", None

    # 4️⃣ Registrar en configuraciones.json
    datos = {}
    if os.path.isfile(CONFIGS_FILE):
        with open(CONFIGS_FILE, 'r') as f:
            try:
                datos = json.load(f)
            except json.JSONDecodeError:
                datos = {}

    datos[cliente] = {
        "vencimiento": vencimiento.strftime("%Y-%m-%d %H:%M"),
        "activa": True
    }

    with open(CONFIGS_FILE, 'w') as f:
        json.dump(datos, f, indent=2)

    # 5️⃣ Devolver éxito y rutas
    return True, conf_path, qr_path
