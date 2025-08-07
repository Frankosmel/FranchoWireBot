# storage.py

import os
import json

def load_json(path: str) -> dict:
    """
    Carga y devuelve un diccionario desde el JSON indicado.
    Si no existe el fichero, crea la carpeta y devuelve {}.
    """
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    if not os.path.isfile(path):
        with open(path, 'w') as f:
            json.dump({}, f, indent=2)
        return {}
    with open(path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_json(path: str, data: dict) -> None:
    """
    Guarda el diccionario en el JSON indicado (reescribe).
    """
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
