"""Núcleo del sistema: persistencia y lógica de negocio."""

from .repository import DataRepository, CargaResultado
from .system import SistemaDonaciones, ResultadoAsignacion
from .loader import construir_sistema

__all__ = [
    "DataRepository",
    "CargaResultado",
    "SistemaDonaciones",
    "ResultadoAsignacion",
    "construir_sistema",
]
