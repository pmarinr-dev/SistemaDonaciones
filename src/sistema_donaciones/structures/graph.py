"""Grafo ponderado y algoritmo de caminos mínimos (Dijkstra).

Modela la red de transporte colombiana:
    - vértices : centros de acopio y municipios afectados.
    - aristas  : carreteras con un peso (distancia en km, tiempo estimado
      u otra métrica de costo). El peso efectivo puede incrementarse según
      el estado de transitabilidad de la vía.

Implementación
--------------
- Lista de adyacencia sobre `HashMap` (nuestra propia tabla hash), no un
  `dict` nativo, para mantener la coherencia con el resto del proyecto.
- Dijkstra con una cola de prioridad binaria mínima implementada a mano
  (`_MinPQ`), sin usar `heapq`.

Complejidad de Dijkstra
-----------------------
Con cola de prioridad binaria: O((V + E) log V).
Adecuado para redes dispersas como una malla vial, donde E ~ O(V).

No se usa A* porque no disponemos de una heurística geográfica fiable
(coordenadas) para todos los nodos sintéticos; Dijkstra garantiza el
óptimo sin heurística. El diseño permite añadir A* reutilizando la misma
cola de prioridad si se incorporan coordenadas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .hash_map import HashMap


class _MinPQ:
    """Cola de prioridad mínima binaria (sobre lista), hecha a mano."""

    def __init__(self) -> None:
        self._data: List[Tuple[float, Any]] = []

    def __len__(self) -> int:
        return len(self._data)

    def push(self, priority: float, item: Any) -> None:
        self._data.append((priority, item))
        self._sift_up(len(self._data) - 1)

    def pop(self) -> Tuple[float, Any]:
        if not self._data:
            raise IndexError("pop sobre cola vacía")
        top = self._data[0]
        last = self._data.pop()
        if self._data:
            self._data[0] = last
            self._sift_down(0)
        return top

    def _sift_up(self, i: int) -> None:
        while i > 0:
            parent = (i - 1) // 2
            if self._data[i][0] < self._data[parent][0]:
                self._data[i], self._data[parent] = self._data[parent], self._data[i]
                i = parent
            else:
                break

    def _sift_down(self, i: int) -> None:
        n = len(self._data)
        while True:
            left, right, smallest = 2 * i + 1, 2 * i + 2, i
            if left < n and self._data[left][0] < self._data[smallest][0]:
                smallest = left
            if right < n and self._data[right][0] < self._data[smallest][0]:
                smallest = right
            if smallest == i:
                break
            self._data[i], self._data[smallest] = self._data[smallest], self._data[i]
            i = smallest


class Graph:
    """Grafo ponderado con lista de adyacencia."""

    def __init__(self, directed: bool = False) -> None:
        self.directed = directed
        # vértice -> HashMap(vecino -> peso)
        self._adj: HashMap = HashMap()

    def add_vertex(self, vertex: Any) -> None:
        if not self._adj.contains(vertex):
            self._adj.set(vertex, HashMap())

    def add_edge(self, u: Any, v: Any, weight: float = 1.0) -> None:
        if weight < 0:
            raise ValueError("Dijkstra no admite pesos negativos")
        self.add_vertex(u)
        self.add_vertex(v)
        self._adj.get(u).set(v, weight)
        if not self.directed:
            self._adj.get(v).set(u, weight)

    def neighbors(self, vertex: Any) -> List[Tuple[Any, float]]:
        if not self._adj.contains(vertex):
            return []
        return list(self._adj.get(vertex).items())

    def vertices(self) -> List[Any]:
        return list(self._adj.keys())

    def has_vertex(self, vertex: Any) -> bool:
        return self._adj.contains(vertex)

    def edge_weight(self, u: Any, v: Any) -> Optional[float]:
        if not self._adj.contains(u):
            return None
        return self._adj.get(u).get(v, None)

    def __len__(self) -> int:
        return len(self._adj)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Graph(vertices={len(self._adj)}, directed={self.directed})"


def dijkstra(graph: Graph, source: Any) -> Tuple[Dict[Any, float], Dict[Any, Any]]:
    """Caminos mínimos desde `source` a todos los vértices alcanzables.

    Devuelve (dist, prev):
        - dist[v] : costo mínimo de source a v (inf si inalcanzable).
        - prev[v] : predecesor de v en el árbol de caminos mínimos.
    """
    if not graph.has_vertex(source):
        raise KeyError(f"Vértice origen inexistente: {source!r}")

    dist: Dict[Any, float] = {v: float("inf") for v in graph.vertices()}
    prev: Dict[Any, Any] = {v: None for v in graph.vertices()}
    dist[source] = 0.0

    visited: set = set()
    pq = _MinPQ()
    pq.push(0.0, source)

    while len(pq) > 0:
        d, u = pq.pop()
        if u in visited:
            continue
        visited.add(u)
        for v, w in graph.neighbors(u):
            if v in visited:
                continue
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                pq.push(nd, v)
    return dist, prev


def shortest_path(graph: Graph, source: Any, target: Any) -> Tuple[List[Any], float]:
    """Ruta más corta concreta source -> target y su costo total.

    Devuelve ([], inf) si target es inalcanzable.
    """
    dist, prev = dijkstra(graph, source)
    if dist.get(target, float("inf")) == float("inf"):
        return [], float("inf")
    path: List[Any] = []
    node: Any = target
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()
    return path, dist[target]
