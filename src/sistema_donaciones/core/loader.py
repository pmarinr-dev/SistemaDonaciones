"""Carga de alto nivel: construye un SistemaDonaciones listo desde un JSON.

Además de las cuatro entidades del dominio, lee la sección opcional
`rutas` para poblar la red de transporte.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

from .repository import CargaResultado, DataRepository
from .system import SistemaDonaciones


def construir_sistema(path: str | Path) -> Tuple[SistemaDonaciones, CargaResultado]:
    """Construye y puebla un sistema a partir de un archivo JSON.

    Devuelve (sistema, carga) donde `carga.errores` lista los registros
    problemáticos encontrados durante el parsing.
    """
    carga = DataRepository.load_json(path)
    sistema = SistemaDonaciones()
    sistema.cargar_desde_resultado(carga)

    # Rutas de la red de transporte (sección opcional).
    for origen, destino, peso in _leer_rutas(path):
        try:
            sistema.agregar_ruta(origen, destino, peso)
        except ValueError as exc:
            carga.errores.append(f"ruta {origen}->{destino}: {exc}")

    return sistema, carga


def _leer_rutas(path: str | Path) -> List[Tuple[str, str, float]]:
    try:
        with Path(path).open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []
    rutas = raw.get("rutas", []) if isinstance(raw, dict) else []
    resultado: List[Tuple[str, str, float]] = []
    for r in rutas or []:
        if not isinstance(r, dict):
            continue
        try:
            resultado.append((str(r["origen"]), str(r["destino"]), float(r["peso"])))
        except (KeyError, TypeError, ValueError):
            continue
    return resultado
