"""Sistema Integral de Gestión y Distribución de Donaciones Post-Desastre.

Paquete principal. Expone la fachada del sistema y las entidades.
"""

from .core import DataRepository, ResultadoAsignacion, SistemaDonaciones
from .models import (
    CategoriaAyuda,
    CentroAcopio,
    Donante,
    EstadoLote,
    LoteAyuda,
    Municipio,
    NivelUrgencia,
)

__version__ = "1.0.0"

__all__ = [
    "SistemaDonaciones",
    "DataRepository",
    "ResultadoAsignacion",
    "CategoriaAyuda",
    "CentroAcopio",
    "Donante",
    "EstadoLote",
    "LoteAyuda",
    "Municipio",
    "NivelUrgencia",
]
