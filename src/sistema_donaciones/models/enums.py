"""Enumeraciones del dominio humanitario."""

from __future__ import annotations

from enum import Enum, IntEnum


class CategoriaAyuda(str, Enum):
    """Categorías de suministros de ayuda humanitaria."""

    MEDICO = "medico"            # insumos médicos / material quirúrgico
    ALIMENTO = "alimento"        # víveres no perecederos
    AGUA = "agua"                # agua potable / potabilizadoras
    REFUGIO = "refugio"          # kits de refugio y herramientas
    FONDOS = "fondos"            # aportes económicos

    @classmethod
    def from_str(cls, value: str) -> "CategoriaAyuda":
        try:
            return cls(value.strip().lower())
        except ValueError as exc:
            raise ValueError(
                f"Categoría inválida: {value!r}. "
                f"Válidas: {[c.value for c in cls]}"
            ) from exc


class EstadoLote(str, Enum):
    """Ciclo de vida de un lote de ayuda dentro del sistema."""

    DISPONIBLE = "disponible"
    ASIGNADO = "asignado"
    DESPACHADO = "despachado"
    VENCIDO = "vencido"


class NivelUrgencia(IntEnum):
    """Nivel de triaje municipal. Mayor valor => mayor urgencia."""

    BAJA = 1
    MEDIA = 2
    ALTA = 3
    CRITICA = 4

    @classmethod
    def from_any(cls, value) -> "NivelUrgencia":
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            return cls(value)
        if isinstance(value, str):
            key = value.strip().upper()
            if key in cls.__members__:
                return cls[key]
            if key.isdigit():
                return cls(int(key))
        raise ValueError(f"Nivel de urgencia inválido: {value!r}")
