# generator.py
#
# Generador de configuraciones WireGuard para clientes.
# - Ejecuta el script bash declarado en config.SCRIPT_PATH para crear el .conf
# - Genera el código QR si no existe
# - Registra/actualiza la metadata de la configuración en configuraciones.json
#
# Retorno de create_config(cliente, plan, vencimiento):
#   (True, ruta_conf, ruta_qr)    en éxito
#   (False, mensaje_error, None)  en error

import os
import subprocess
from datetime import datetime

from config import SCRIPT_PATH, CLIENTS_DIR
from utils import (
    ruta_conf_cliente,
    ruta_qr_cliente,
    generate_qr,
    registrar_config,  # Debe existir en utils.py
)


def create_config(cliente: str, plan: str, vencimiento: datetime):
    """
    Crea una configuración WireGuard para un cliente.

    Pasos:
      1) Ejecuta el script bash (SCRIPT_PATH) que debe generar el archivo .conf
      2) Comprueba la existencia del .conf y genera el QR si no existe
      3) Registra la configuración (plan, vencimiento, activa) en configuraciones.json

    Args:
        cliente (str): nombre/identificador del cliente (se usa para el nombre de archivo)
        plan (str): nombre del plan seleccionado (debe existir en config.PLANS)
        vencimiento (datetime): fecha/hora exacta de vencimiento

    Returns:
        tuple:
            (True, conf_path, qr_path)              si todo salió bien
            (False, mensaje_error, None)            si hubo error
    """
    try:
        # Asegurar carpeta de clientes
        os.makedirs(CLIENTS_DIR, exist_ok=True)

        # 1) Ejecutar el script que crea la configuración del cliente
        #    El script debe aceptar como argumento el nombre del cliente
        #    y generar el archivo: {CLIENTS_DIR}/{cliente}.conf
        result = subprocess.run(
            ["sudo", "bash", SCRIPT_PATH, cliente],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # stderr suele contener el motivo del fallo
            return False, (result.stderr or "Error desconocido al ejecutar el script"), None

        # 2) Verificar rutas generadas por el script
        conf_path = ruta_conf_cliente(cliente)
        qr_path = ruta_qr_cliente(cliente)

        if not os.path.isfile(conf_path):
            return False, f"No se encontró el archivo de configuración: {conf_path}", None

        # Generar QR si aún no existe
        if not os.path.isfile(qr_path):
            try:
                generate_qr(conf_path)  # genera el PNG a partir del .conf
            except Exception as e:
                return False, f"Error al generar el QR: {e}", None

        # 3) Registrar/actualizar en configuraciones.json (fuente de verdad)
        try:
            registrar_config(cliente, plan, vencimiento)
        except Exception as e:
            return False, f"Error al registrar la configuración en JSON: {e}", None

        # Éxito
        return True, conf_path, qr_path

    except Exception as e:
        # Cualquier otra excepción no controlada
        return False, f"Excepción no controlada en create_config: {e}", None
