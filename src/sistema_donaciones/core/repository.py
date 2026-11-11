"""Persistencia e intercambio de datos (Fase 1).

Lectura/escritura en JSON y CSV con manejo robusto de errores de I/O y
de registros mal estructurados o nulos. Los registros inválidos no
abortan toda la carga: se recolectan como errores y se omiten, de modo
que un archivo parcialmente corrupto siga siendo aprovechable.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..models import CentroAcopio, Donante, LoteAyuda, Municipio


@dataclass
class CargaResultado:
    """Resultado de una carga: entidades válidas + errores por registro."""

    donantes: List[Donante] = field(default_factory=list)
    lotes: List[LoteAyuda] = field(default_factory=list)
    centros: List[CentroAcopio] = field(default_factory=list)
    municipios: List[Municipio] = field(default_factory=list)
    errores: List[str] = field(default_factory=list)

    def resumen(self) -> str:
        return (
            f"{len(self.donantes)} donantes, {len(self.lotes)} lotes, "
            f"{len(self.centros)} centros, {len(self.municipios)} municipios, "
            f"{len(self.errores)} errores"
        )


_PARSERS = {
    "donantes": Donante.from_dict,
    "lotes": LoteAyuda.from_dict,
    "centros": CentroAcopio.from_dict,
    "municipios": Municipio.from_dict,
}


class DataRepository:
    """Lee y escribe entidades del dominio desde/hacia disco."""

    # ------------------------------------------------------------------ #
    # JSON
    # ------------------------------------------------------------------ #
    @staticmethod
    def load_json(path: str | Path) -> CargaResultado:
        """Carga un JSON con claves donantes/lotes/centros/municipios.

        Registros nulos o mal estructurados se reportan en `errores` y se
        omiten; nunca propagan una excepción que tumbe toda la carga.
        """
        path = Path(path)
        resultado = CargaResultado()
        try:
            with path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except FileNotFoundError:
            resultado.errores.append(f"Archivo no encontrado: {path}")
            return resultado
        except json.JSONDecodeError as exc:
            resultado.errores.append(f"JSON inválido en {path}: {exc}")
            return resultado
        except OSError as exc:
            resultado.errores.append(f"Error de E/S leyendo {path}: {exc}")
            return resultado

        if not isinstance(raw, dict):
            resultado.errores.append("El JSON raíz debe ser un objeto/diccionario")
            return resultado

        for seccion, parser in _PARSERS.items():
            registros = raw.get(seccion, []) or []
            if not isinstance(registros, list):
                resultado.errores.append(f"La sección '{seccion}' no es una lista")
                continue
            destino = getattr(resultado, seccion)
            for i, registro in enumerate(registros):
                if registro is None:
                    resultado.errores.append(f"{seccion}[{i}]: registro nulo omitido")
                    continue
                try:
                    destino.append(parser(registro))
                except (ValueError, KeyError, TypeError) as exc:
                    resultado.errores.append(f"{seccion}[{i}]: {exc}")
        return resultado

    @staticmethod
    def save_json(path: str | Path, resultado: CargaResultado) -> None:
        path = Path(path)
        data = {
            "donantes": [d.to_dict() for d in resultado.donantes],
            "lotes": [l.to_dict() for l in resultado.lotes],
            "centros": [c.to_dict() for c in resultado.centros],
            "municipios": [m.to_dict() for m in resultado.municipios],
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise IOError(f"No se pudo escribir {path}: {exc}") from exc

    # ------------------------------------------------------------------ #
    # CSV (una entidad por archivo)
    # ------------------------------------------------------------------ #
    @staticmethod
    def load_csv(path: str | Path, entidad: str) -> Tuple[List[Any], List[str]]:
        """Carga una lista de entidades de un CSV. `entidad` es una de las
        claves de _PARSERS. Devuelve (entidades, errores)."""
        if entidad not in _PARSERS:
            raise ValueError(f"Entidad desconocida: {entidad}")
        path = Path(path)
        parser = _PARSERS[entidad]
        entidades: List[Any] = []
        errores: List[str] = []
        try:
            with path.open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for i, fila in enumerate(reader):
                    try:
                        # CSV: necesidades vienen como "cat:cant;cat:cant"
                        if entidad == "municipios" and fila.get("necesidades"):
                            fila["necesidades"] = _parse_necesidades_csv(
                                fila["necesidades"]
                            )
                        entidades.append(parser(fila))
                    except (ValueError, KeyError, TypeError) as exc:
                        errores.append(f"{entidad} fila {i}: {exc}")
        except FileNotFoundError:
            errores.append(f"Archivo no encontrado: {path}")
        except OSError as exc:
            errores.append(f"Error de E/S leyendo {path}: {exc}")
        return entidades, errores


def _parse_necesidades_csv(texto: str) -> Dict[str, int]:
    """'medico:100;agua:50' -> {'medico': 100, 'agua': 50}."""
    resultado: Dict[str, int] = {}
    for par in texto.split(";"):
        par = par.strip()
        if not par:
            continue
        cat, _, cant = par.partition(":")
        resultado[cat.strip()] = int(cant.strip())
    return resultado
