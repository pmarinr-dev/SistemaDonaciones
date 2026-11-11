"""Modelos del dominio (Fase 1): entidades fuertemente tipadas.

Entidades:
    - Donante
    - LoteAyuda (con caducidad, tipo, peso, volumen, condición de frío)
    - CentroAcopio
    - Municipio (con nivel de urgencia y necesidades cuantitativas)

Enumeraciones de apoyo: CategoriaAyuda, EstadoLote, NivelUrgencia.
"""

from .enums import CategoriaAyuda, EstadoLote, NivelUrgencia
from .entities import Donante, LoteAyuda, CentroAcopio, Municipio

__all__ = [
    "CategoriaAyuda",
    "EstadoLote",
    "NivelUrgencia",
    "Donante",
    "LoteAyuda",
    "CentroAcopio",
    "Municipio",
]
