"""Entidades del dominio con validación estricta y (de)serialización.

Se usan dataclasses con validación en __post_init__. Las entidades de
referencia que no deberían mutar tras su creación (Donante) se declaran
`frozen=True` (inmutabilidad donde aplica, como pide la rúbrica).

La fecha del evento sísmico (EVENTO_FECHA) es la referencia temporal:
toda fecha de caducidad debe ser POSTERIOR al evento.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from .enums import CategoriaAyuda, EstadoLote, NivelUrgencia

# Fecha de referencia del evento sísmico que originó la emergencia.
EVENTO_FECHA: date = date(2026, 1, 15)


def _parse_fecha(value: Any) -> date:
    """Convierte str ISO (YYYY-MM-DD) o date/datetime a `date`."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValueError(f"Fecha inválida (use YYYY-MM-DD): {value!r}") from exc
    raise ValueError(f"Tipo de fecha no soportado: {type(value).__name__}")


# --------------------------------------------------------------------------- #
# Donante (inmutable)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Donante:
    """Entidad donante. Inmutable: una vez registrado no cambia."""

    id: str
    nombre: str
    tipo: str  # "persona", "ong", "empresa", "internacional"
    pais: str = "Colombia"

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise ValueError("Donante.id no puede estar vacío")
        if not self.nombre or not str(self.nombre).strip():
            raise ValueError("Donante.nombre no puede estar vacío")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Donante":
        return cls(
            id=str(data["id"]),
            nombre=str(data["nombre"]),
            tipo=str(data.get("tipo", "persona")),
            pais=str(data.get("pais", "Colombia")),
        )


# --------------------------------------------------------------------------- #
# Lote de Ayuda
# --------------------------------------------------------------------------- #
@dataclass
class LoteAyuda:
    """Lote de suministros donado.

    Atributos requeridos por el enunciado: caducidad, tipo (categoría),
    peso, volumen y condición de frío (cadena de frío).
    """

    id: str
    categoria: CategoriaAyuda
    descripcion: str
    cantidad: int
    peso_kg: float
    volumen_m3: float
    requiere_frio: bool
    fecha_caducidad: date
    donante_id: str
    estado: EstadoLote = EstadoLote.DISPONIBLE
    municipio_destino: Optional[str] = None

    def __post_init__(self) -> None:
        # Normalización de tipos.
        if not isinstance(self.categoria, CategoriaAyuda):
            self.categoria = CategoriaAyuda.from_str(str(self.categoria))
        if not isinstance(self.estado, EstadoLote):
            self.estado = EstadoLote(str(self.estado))
        self.fecha_caducidad = _parse_fecha(self.fecha_caducidad)

        # Validación de rangos (cantidades no negativas).
        if not self.id or not str(self.id).strip():
            raise ValueError("LoteAyuda.id no puede estar vacío")
        if self.cantidad < 0:
            raise ValueError("cantidad no puede ser negativa")
        if self.peso_kg < 0:
            raise ValueError("peso_kg no puede ser negativo")
        if self.volumen_m3 < 0:
            raise ValueError("volumen_m3 no puede ser negativo")

        # Coherencia temporal: caducidad posterior al evento.
        # Los fondos económicos no caducan: se les exige igualmente una
        # fecha válida pero no se restringe su vigencia.
        if (
            self.categoria is not CategoriaAyuda.FONDOS
            and self.fecha_caducidad <= EVENTO_FECHA
        ):
            raise ValueError(
                f"fecha_caducidad ({self.fecha_caducidad}) debe ser posterior "
                f"al evento ({EVENTO_FECHA})"
            )

    # -- utilidades de negocio -------------------------------------------- #
    def dias_para_caducar(self, referencia: Optional[date] = None) -> int:
        ref = referencia or EVENTO_FECHA
        return (self.fecha_caducidad - ref).days

    def esta_disponible(self) -> bool:
        return self.estado is EstadoLote.DISPONIBLE

    def clave_caducidad(self) -> int:
        """Clave entera YYYYMMDD para indexación en el árbol AVL."""
        f = self.fecha_caducidad
        return f.year * 10000 + f.month * 100 + f.day

    # -- (de)serialización ------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "categoria": self.categoria.value,
            "descripcion": self.descripcion,
            "cantidad": self.cantidad,
            "peso_kg": self.peso_kg,
            "volumen_m3": self.volumen_m3,
            "requiere_frio": self.requiere_frio,
            "fecha_caducidad": self.fecha_caducidad.isoformat(),
            "donante_id": self.donante_id,
            "estado": self.estado.value,
            "municipio_destino": self.municipio_destino,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoteAyuda":
        if data is None:
            raise ValueError("Registro de lote nulo")
        try:
            return cls(
                id=str(data["id"]),
                categoria=data["categoria"],
                descripcion=str(data.get("descripcion", "")),
                cantidad=int(data["cantidad"]),
                peso_kg=float(data["peso_kg"]),
                volumen_m3=float(data["volumen_m3"]),
                requiere_frio=bool(data.get("requiere_frio", False)),
                fecha_caducidad=data["fecha_caducidad"],
                donante_id=str(data["donante_id"]),
                estado=data.get("estado", EstadoLote.DISPONIBLE.value),
                municipio_destino=data.get("municipio_destino"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Lote mal estructurado: {exc}") from exc


# --------------------------------------------------------------------------- #
# Centro de Acopio
# --------------------------------------------------------------------------- #
@dataclass
class CentroAcopio:
    """Centro de acopio intermedio (nodo de distribución)."""

    id: str
    nombre: str
    ciudad: str
    capacidad_m3: float
    tiene_cadena_frio: bool = False

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise ValueError("CentroAcopio.id no puede estar vacío")
        if self.capacidad_m3 < 0:
            raise ValueError("capacidad_m3 no puede ser negativa")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CentroAcopio":
        return cls(
            id=str(data["id"]),
            nombre=str(data["nombre"]),
            ciudad=str(data.get("ciudad", "")),
            capacidad_m3=float(data["capacidad_m3"]),
            tiene_cadena_frio=bool(data.get("tiene_cadena_frio", False)),
        )


# --------------------------------------------------------------------------- #
# Municipio Afectado
# --------------------------------------------------------------------------- #
@dataclass
class Municipio:
    """Municipio afectado con nivel de urgencia y necesidades cuantitativas.

    `necesidades` mapea CategoriaAyuda.value -> cantidad requerida.
    """

    id: str
    nombre: str
    departamento: str
    nivel_urgencia: NivelUrgencia
    poblacion: int
    necesidades: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise ValueError("Municipio.id no puede estar vacío")
        self.nivel_urgencia = NivelUrgencia.from_any(self.nivel_urgencia)
        if self.poblacion < 0:
            raise ValueError("poblacion no puede ser negativa")
        # Validar necesidades: categorías válidas y cantidades no negativas.
        limpio: Dict[str, int] = {}
        for cat, cant in (self.necesidades or {}).items():
            categoria = CategoriaAyuda.from_str(str(cat))
            c = int(cant)
            if c < 0:
                raise ValueError(f"Necesidad negativa para {cat}")
            limpio[categoria.value] = c
        self.necesidades = limpio

    def necesidad_total(self) -> int:
        return sum(self.necesidades.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "departamento": self.departamento,
            "nivel_urgencia": int(self.nivel_urgencia),
            "poblacion": self.poblacion,
            "necesidades": dict(self.necesidades),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Municipio":
        if data is None:
            raise ValueError("Registro de municipio nulo")
        try:
            return cls(
                id=str(data["id"]),
                nombre=str(data["nombre"]),
                departamento=str(data.get("departamento", "")),
                nivel_urgencia=data["nivel_urgencia"],
                poblacion=int(data["poblacion"]),
                necesidades=dict(data.get("necesidades", {})),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Municipio mal estructurado: {exc}") from exc
