"""Lógica de negocio del sistema de donaciones (Fase 2).

Orquesta las cuatro estructuras de datos de la Fase 3:

    - HashMap   : índices O(1) de donantes, centros, municipios y lotes.
    - MinMaxHeap: cola de triaje de municipios por nivel de urgencia.
    - AVLTree   : índice ordenado de lotes por fecha de caducidad para
                  consultas de rango y priorización de lo que vence antes.
    - Graph     : red de transporte para calcular rutas de despacho.

Operaciones del catálogo (enunciado):
    - registrar donaciones entrantes (categorización instantánea).
    - búsqueda multinivel (por id, por categoría, por caducidad próxima).
    - asignación automatizada según triaje/urgencia municipal.
    - informes en tiempo real (balance de stock, despachados vs. remanentes,
      alertas tempranas de desabastecimiento).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple

from ..models import (
    CategoriaAyuda,
    CentroAcopio,
    Donante,
    EstadoLote,
    LoteAyuda,
    Municipio,
    NivelUrgencia,
)
from ..models.entities import EVENTO_FECHA
from ..structures import AVLTree, Graph, HashMap, MinMaxHeap, dijkstra
from ..structures.graph import shortest_path


@dataclass
class ResultadoAsignacion:
    """Resultado de asignar un lote a un municipio."""

    lote_id: str
    municipio_id: str
    categoria: str
    cantidad: int
    ruta: List[str] = field(default_factory=list)
    costo_ruta: float = 0.0

    def __str__(self) -> str:
        ruta_txt = " -> ".join(self.ruta) if self.ruta else "sin ruta"
        return (
            f"Lote {self.lote_id} ({self.categoria} x{self.cantidad}) "
            f"-> {self.municipio_id} | ruta: {ruta_txt} ({self.costo_ruta:.1f})"
        )


class SistemaDonaciones:
    """Fachada que coordina estructuras de datos y reglas de negocio."""

    def __init__(self) -> None:
        # Índices hash O(1).
        self._donantes: HashMap = HashMap()
        self._centros: HashMap = HashMap()
        self._municipios: HashMap = HashMap()
        self._lotes: HashMap = HashMap()  # id -> LoteAyuda

        # Índice ordenado por fecha de caducidad (clave YYYYMMDD).
        self._arbol_caducidad: AVLTree = AVLTree()

        # Red de transporte.
        self.red: Graph = Graph(directed=False)

    # ================================================================== #
    # Registro de entidades
    # ================================================================== #
    def registrar_donante(self, donante: Donante) -> None:
        self._donantes.set(donante.id, donante)

    def registrar_centro(self, centro: CentroAcopio) -> None:
        self._centros.set(centro.id, centro)
        self.red.add_vertex(centro.id)

    def registrar_municipio(self, municipio: Municipio) -> None:
        self._municipios.set(municipio.id, municipio)
        self.red.add_vertex(municipio.id)

    def registrar_donacion(self, lote: LoteAyuda) -> None:
        """Registra un lote entrante y lo indexa (categorización instantánea).

        Valida que el donante exista. Indexa en el hash de lotes y en el
        árbol AVL por fecha de caducidad.
        """
        if not self._donantes.contains(lote.donante_id):
            raise ValueError(f"Donante inexistente: {lote.donante_id}")
        if self._lotes.contains(lote.id):
            raise ValueError(f"Lote duplicado: {lote.id}")
        self._lotes.set(lote.id, lote)
        self._arbol_caducidad.insert(lote.clave_caducidad(), lote.id)

    def agregar_ruta(self, origen: str, destino: str, peso: float) -> None:
        """Agrega una carretera (arista) a la red de transporte."""
        self.red.add_edge(origen, destino, peso)

    # ================================================================== #
    # Búsqueda multinivel
    # ================================================================== #
    def buscar_lote(self, lote_id: str) -> Optional[LoteAyuda]:
        """Búsqueda por identificador único. O(1)."""
        return self._lotes.get(lote_id, None)

    def buscar_por_categoria(
        self, categoria: CategoriaAyuda, solo_disponibles: bool = True
    ) -> List[LoteAyuda]:
        """Todos los lotes de una categoría. O(n)."""
        cat = (
            categoria
            if isinstance(categoria, CategoriaAyuda)
            else CategoriaAyuda.from_str(str(categoria))
        )
        res = []
        for lote in self._lotes.values():
            if lote.categoria is cat and (
                not solo_disponibles or lote.esta_disponible()
            ):
                res.append(lote)
        return res

    def buscar_proximos_a_caducar(
        self, dias: int, referencia: Optional[date] = None
    ) -> List[LoteAyuda]:
        """Lotes que caducan dentro de `dias` a partir de la referencia.

        Usa el árbol AVL para una consulta de rango O(log n + k).
        """
        ref = referencia or EVENTO_FECHA
        low = ref.year * 10000 + ref.month * 100 + ref.day
        limite = date.fromordinal(ref.toordinal() + max(dias, 0))
        high = limite.year * 10000 + limite.month * 100 + limite.day
        pares = self._arbol_caducidad.range_query(low, high)
        lotes = []
        for _, lote_id in pares:
            lote = self._lotes.get(lote_id, None)
            if lote is not None and lote.esta_disponible():
                lotes.append(lote)
        return lotes

    # ================================================================== #
    # Asignación automatizada por triaje
    # ================================================================== #
    def _cola_triaje(self) -> MinMaxHeap:
        """Construye una cola min-max de municipios por nivel de urgencia.

        La prioridad combina urgencia (peso dominante) y necesidad total,
        de modo que a igual urgencia se atiende primero a quien más
        necesita. Extraer el máximo da el municipio más crítico.
        """
        heap = MinMaxHeap(
            key=lambda m: (int(m.nivel_urgencia), m.necesidad_total())
        )
        for municipio in self._municipios.values():
            if municipio.necesidad_total() > 0:
                heap.push(municipio)
        return heap

    def asignar_recursos(
        self, centro_origen: Optional[str] = None
    ) -> List[ResultadoAsignacion]:
        """Asigna lotes disponibles a municipios según prioridad de triaje.

        Algoritmo:
            1. Construir cola min-max de municipios con necesidades.
            2. Mientras haya municipios pendientes, extraer el MÁS urgente.
            3. Para cada categoría que necesita, tomar lotes disponibles
               priorizando los que caducan antes (vía árbol AVL).
            4. Marcar los lotes como ASIGNADO y calcular la ruta de despacho
               desde el centro de origen (Dijkstra) si se indica.
        """
        asignaciones: List[ResultadoAsignacion] = []
        cola = self._cola_triaje()
        # Copia mutable de necesidades para no alterar los municipios.
        pendientes: Dict[str, Dict[str, int]] = {
            m.id: dict(m.necesidades) for m in self._municipios.values()
        }

        while not cola.is_empty():
            municipio = cola.pop_max()
            necesidades = pendientes.get(municipio.id, {})
            for categoria_val, requerido in list(necesidades.items()):
                if requerido <= 0:
                    continue
                categoria = CategoriaAyuda.from_str(categoria_val)
                restante = requerido
                for lote in self._lotes_disponibles_por_caducidad(categoria):
                    if restante <= 0:
                        break
                    tomar = min(restante, lote.cantidad)
                    lote.estado = EstadoLote.ASIGNADO
                    lote.municipio_destino = municipio.id
                    ruta, costo = self._ruta_despacho(centro_origen, municipio.id)
                    asignaciones.append(
                        ResultadoAsignacion(
                            lote_id=lote.id,
                            municipio_id=municipio.id,
                            categoria=categoria.value,
                            cantidad=tomar,
                            ruta=ruta,
                            costo_ruta=costo,
                        )
                    )
                    restante -= tomar
                necesidades[categoria_val] = max(restante, 0)
        return asignaciones

    def _lotes_disponibles_por_caducidad(
        self, categoria: CategoriaAyuda
    ) -> List[LoteAyuda]:
        """Lotes disponibles de una categoría, ordenados por caducidad asc.

        Recorre el árbol AVL en orden (los que caducan antes salen primero),
        respetando el principio FEFO (First-Expired-First-Out).
        """
        resultado: List[LoteAyuda] = []
        for _, lote_id in self._arbol_caducidad.in_order():
            lote = self._lotes.get(lote_id, None)
            if (
                lote is not None
                and lote.esta_disponible()
                and lote.categoria is categoria
            ):
                resultado.append(lote)
        return resultado

    def _ruta_despacho(
        self, origen: Optional[str], destino: str
    ) -> Tuple[List[str], float]:
        if not origen or not self.red.has_vertex(origen):
            return [], 0.0
        if not self.red.has_vertex(destino):
            return [], 0.0
        return shortest_path(self.red, origen, destino)

    def despachar(self, lote_id: str) -> None:
        """Marca un lote ASIGNADO como DESPACHADO."""
        lote = self._lotes.get(lote_id, None)
        if lote is None:
            raise ValueError(f"Lote inexistente: {lote_id}")
        if lote.estado is not EstadoLote.ASIGNADO:
            raise ValueError(
                f"Solo se despachan lotes asignados (estado actual: {lote.estado.value})"
            )
        lote.estado = EstadoLote.DESPACHADO

    # ================================================================== #
    # Rutas óptimas
    # ================================================================== #
    def ruta_optima(self, origen: str, destino: str) -> Tuple[List[str], float]:
        """Ruta de costo mínimo entre dos nodos de la red."""
        return shortest_path(self.red, origen, destino)

    def distancias_desde(self, origen: str) -> Dict[str, float]:
        dist, _ = dijkstra(self.red, origen)
        return dist

    # ================================================================== #
    # Informes en tiempo real
    # ================================================================== #
    def balance_stock(self) -> Dict[str, Dict[str, int]]:
        """Balance por categoría: disponible / asignado / despachado / vencido."""
        balance: Dict[str, Dict[str, int]] = {}
        for lote in self._lotes.values():
            cat = lote.categoria.value
            fila = balance.setdefault(
                cat,
                {"disponible": 0, "asignado": 0, "despachado": 0, "vencido": 0},
            )
            fila[lote.estado.value] = fila.get(lote.estado.value, 0) + lote.cantidad
        return balance

    def despachados_vs_remanentes(self) -> Dict[str, int]:
        despachados = 0
        remanentes = 0
        for lote in self._lotes.values():
            if lote.estado is EstadoLote.DESPACHADO:
                despachados += lote.cantidad
            elif lote.estado in (EstadoLote.DISPONIBLE, EstadoLote.ASIGNADO):
                remanentes += lote.cantidad
        return {"despachados": despachados, "remanentes": remanentes}

    def alertas_desabastecimiento(self) -> List[Dict[str, object]]:
        """Alertas tempranas: categorías donde la demanda supera el stock
        disponible. Una alerta por categoría deficitaria."""
        demanda: Dict[str, int] = {}
        for municipio in self._municipios.values():
            for cat, cant in municipio.necesidades.items():
                demanda[cat] = demanda.get(cat, 0) + cant

        disponible: Dict[str, int] = {}
        for lote in self._lotes.values():
            if lote.esta_disponible():
                disponible[lote.categoria.value] = (
                    disponible.get(lote.categoria.value, 0) + lote.cantidad
                )

        alertas: List[Dict[str, object]] = []
        for cat, req in demanda.items():
            disp = disponible.get(cat, 0)
            if req > disp:
                alertas.append(
                    {
                        "categoria": cat,
                        "demanda": req,
                        "disponible": disp,
                        "deficit": req - disp,
                    }
                )
        alertas.sort(key=lambda a: a["deficit"], reverse=True)  # type: ignore[arg-type]
        return alertas

    def marcar_vencidos(self, referencia: Optional[date] = None) -> List[str]:
        """Marca como VENCIDO los lotes caducados a la fecha de referencia.

        Devuelve los ids afectados. Los fondos económicos no caducan.
        """
        ref = referencia or EVENTO_FECHA
        vencidos: List[str] = []
        for lote in self._lotes.values():
            if lote.categoria is CategoriaAyuda.FONDOS:
                continue
            if (
                lote.estado in (EstadoLote.DISPONIBLE, EstadoLote.ASIGNADO)
                and lote.fecha_caducidad < ref
            ):
                lote.estado = EstadoLote.VENCIDO
                vencidos.append(lote.id)
        return vencidos

    # ================================================================== #
    # Accesores
    # ================================================================== #
    @property
    def donantes(self) -> HashMap:
        return self._donantes

    @property
    def centros(self) -> HashMap:
        return self._centros

    @property
    def municipios(self) -> HashMap:
        return self._municipios

    @property
    def lotes(self) -> HashMap:
        return self._lotes

    def cargar_desde_resultado(self, carga) -> None:
        """Puebla el sistema desde un CargaResultado del repositorio."""
        for d in carga.donantes:
            self.registrar_donante(d)
        for c in carga.centros:
            self.registrar_centro(c)
        for m in carga.municipios:
            self.registrar_municipio(m)
        for l in carga.lotes:
            try:
                self.registrar_donacion(l)
            except ValueError:
                # lote con donante inexistente o duplicado: se omite
                pass
