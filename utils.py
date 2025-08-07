# utils.py

import os
import subprocess
import ipaddress
import json
import qrcode
from io import BytesIO
from datetime import datetime, timedelta

from config import (
    WG_CONFIG_DIR,
    CLIENTS_DIR,            # Ajustado al nombre definido en config.py
    IP_RANGO_INICIO,
    IP_RANGO_FIN,
    SERVER_PUBLIC_IP,
    LISTEN_PORT,
    SERVER_PUBLIC_KEY
)

# ========================= RUTAS =========================

def ruta_conf_cliente(nombre: str) -> str:
    """
    Devuelve la ruta absoluta del archivo .conf de un cliente.
    """
    return os.path.join(WG_CONFIG_DIR, f"{nombre}.conf")


# ========================= GESTIÓN DE CLIENTES =========================

def calcular_vencimiento(dias: int) -> str:
    """
    Calcula la fecha de vencimiento a partir de los días proporcionados.
    """
    vencimiento = datetime.now() + timedelta(days=dias)
    return vencimiento.strftime("%Y-%m-%d %H:%M")


def cargar_cliente(nombre: str):
    """
    Carga los datos del cliente desde su archivo JSON.
    """
    ruta = os.path.join(CLIENTS_DIR, f"{nombre}.json")
    if not os.path.exists(ruta):
        return None
    with open(ruta, "r") as f:
        return json.load(f)


def obtener_ips_asignadas():
    """
    Devuelve una lista de todas las IPs asignadas actualmente a los clientes.
    """
    ips = []
    for archivo in os.listdir(CLIENTS_DIR):
        if archivo.endswith(".json"):
            ruta = os.path.join(CLIENTS_DIR, archivo)
            with open(ruta, "r") as f:
                data = json.load(f)
                ip = data.get("ip")
                if ip:
                    ips.append(ip)
    return ips


def asignar_ip_disponible():
    """
    Busca la próxima IP disponible dentro del rango definido.
    """
    usadas = obtener_ips_asignadas()
    inicio = ipaddress.IPv4Address(IP_RANGO_INICIO)
    fin = ipaddress.IPv4Address(IP_RANGO_FIN)

    for ip_int in range(int(inicio), int(fin) + 1):
        ip_str = str(ipaddress.IPv4Address(ip_int))
        if ip_str not in usadas:
            return ip_str
    raise RuntimeError("❌ No hay IPs disponibles en el rango definido.")


# ========================= CÓDIGO QR =========================

def generar_qr_desde_conf(ruta_archivo: str):
    """
    Genera un código QR desde el contenido de un archivo .conf.
    Devuelve un objeto BytesIO con la imagen PNG.
    """
    if not os.path.exists(ruta_archivo):
        return None
    with open(ruta_archivo, "r") as f:
        contenido = f.read()
    qr = qrcode.make(contenido)
    bio = BytesIO()
    qr.save(bio, format="PNG")
    bio.seek(0)
    return bio
