"""Min-Max Heap: cola de prioridad doble.

Permite consultar y extraer en O(1)/O(log n) tanto el elemento de MENOR
prioridad como el de MAYOR prioridad, usando un único arreglo.

Motivación en el dominio
-------------------------
El triaje humanitario necesita dos consultas simétricas sobre la misma
cola de solicitudes:
    - "atender primero al municipio más urgente"  -> extraer el MÁXIMO.
    - "descartar/revisar la solicitud menos urgente" -> consultar el MÍNIMO.
Un min-max heap da ambas operaciones con el mismo almacenamiento, evitando
mantener dos heaps separados.

Estructura
----------
Arreglo con raíz en el índice 0. Los niveles se alternan:
    - niveles PAR  (0, 2, 4, ...) son niveles "min": el nodo es <= que
      todos sus descendientes.
    - niveles IMPAR (1, 3, ...)   son niveles "max": el nodo es >= que
      todos sus descendientes.

Complejidad
-----------
- peek_min / peek_max : O(1)
- push                : O(log n)
- pop_min / pop_max   : O(log n)

Cada elemento se inserta como una tupla (clave_prioridad, contador, payload).
El `contador` monotónico desempata y garantiza orden FIFO estable entre
elementos de igual prioridad, además de evitar comparar los payloads.
"""

from __future__ import annotations

from typing import Any, Callable, List, Tuple


class MinMaxHeap:
    """Cola de prioridad doble basada en un arreglo min-max.

    Parameters
    ----------
    key:
        Función que extrae de cada payload el valor de prioridad usado
        para ordenar. Un valor mayor => mayor prioridad. Por defecto es
        la identidad.
    """

    def __init__(self, key: Callable[[Any], Any] = lambda x: x) -> None:
        self._key = key
        self._data: List[Tuple[Any, int, Any]] = []
        self._counter: int = 0

    # ------------------------------------------------------------------ #
    # Helpers de navegación por el arreglo
    # ------------------------------------------------------------------ #
    @staticmethod
    def _level(index: int) -> int:
        """Nivel (profundidad) del nodo en el índice dado."""
        return (index + 1).bit_length() - 1

    @staticmethod
    def _is_min_level(index: int) -> bool:
        return MinMaxHeap._level(index) % 2 == 0

    @staticmethod
    def _parent(index: int) -> int:
        return (index - 1) // 2

    @staticmethod
    def _has_parent(index: int) -> bool:
        return index > 0

    def _children(self, index: int) -> List[int]:
        left, right = 2 * index + 1, 2 * index + 2
        return [c for c in (left, right) if c < len(self._data)]

    def _descendants(self, index: int) -> List[int]:
        """Hijos y nietos del nodo (los que importan en un min-max heap)."""
        result: List[int] = []
        for child in self._children(index):
            result.append(child)
            result.extend(self._children(child))
        return result

    def _prio(self, index: int) -> Tuple[Any, int]:
        """Clave de comparación: (prioridad, contador) para orden estable."""
        _, counter, _ = self._data[index]
        key_value, _, _ = self._data[index]
        return (key_value, counter)

    def _swap(self, i: int, j: int) -> None:
        self._data[i], self._data[j] = self._data[j], self._data[i]

    # ------------------------------------------------------------------ #
    # Restauración de la propiedad del heap
    # ------------------------------------------------------------------ #
    def _push_up(self, index: int) -> None:
        if not self._has_parent(index):
            return
        parent = self._parent(index)
        if self._is_min_level(index):
            if self._prio(index) > self._prio(parent):
                self._swap(index, parent)
                self._push_up_max(parent)
            else:
                self._push_up_min(index)
        else:
            if self._prio(index) < self._prio(parent):
                self._swap(index, parent)
                self._push_up_min(parent)
            else:
                self._push_up_max(index)

    def _push_up_min(self, index: int) -> None:
        while self._has_parent(index):
            grandparent = self._parent(self._parent(index))
            if self._parent(index) > 0 and self._prio(index) < self._prio(grandparent):
                self._swap(index, grandparent)
                index = grandparent
            else:
                break

    def _push_up_max(self, index: int) -> None:
        while self._has_parent(index):
            if self._parent(index) == 0:
                break
            grandparent = self._parent(self._parent(index))
            if self._prio(index) > self._prio(grandparent):
                self._swap(index, grandparent)
                index = grandparent
            else:
                break

    def _push_down(self, index: int) -> None:
        if self._is_min_level(index):
            self._push_down_min(index)
        else:
            self._push_down_max(index)

    def _push_down_min(self, index: int) -> None:
        while True:
            descendants = self._descendants(index)
            if not descendants:
                return
            smallest = min(descendants, key=self._prio)
            if self._prio(smallest) >= self._prio(index):
                return
            self._swap(smallest, index)
            # ¿es nieto?
            if smallest > 2 * index + 2:
                parent = self._parent(smallest)
                if self._prio(smallest) > self._prio(parent):
                    self._swap(smallest, parent)
                index = smallest
            else:
                return

    def _push_down_max(self, index: int) -> None:
        while True:
            descendants = self._descendants(index)
            if not descendants:
                return
            largest = max(descendants, key=self._prio)
            if self._prio(largest) <= self._prio(index):
                return
            self._swap(largest, index)
            if largest > 2 * index + 2:
                parent = self._parent(largest)
                if self._prio(largest) < self._prio(parent):
                    self._swap(largest, parent)
                index = largest
            else:
                return

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def push(self, payload: Any) -> None:
        """Agrega un elemento. O(log n)."""
        key_value = self._key(payload)
        self._data.append((key_value, self._counter, payload))
        self._counter += 1
        self._push_up(len(self._data) - 1)

    def peek_min(self) -> Any:
        """Elemento de MENOR prioridad sin extraerlo. O(1)."""
        if not self._data:
            raise IndexError("peek_min sobre heap vacío")
        return self._data[0][2]

    def peek_max(self) -> Any:
        """Elemento de MAYOR prioridad sin extraerlo. O(1)."""
        if not self._data:
            raise IndexError("peek_max sobre heap vacío")
        max_index = self._max_index()
        return self._data[max_index][2]

    def _max_index(self) -> int:
        """Índice del máximo: raíz o el mayor de sus dos hijos (nivel max)."""
        if len(self._data) == 1:
            return 0
        children = self._children(0)
        return max(children, key=self._prio)

    def pop_min(self) -> Any:
        """Extrae y devuelve el elemento de MENOR prioridad. O(log n)."""
        if not self._data:
            raise IndexError("pop_min sobre heap vacío")
        return self._pop_at(0)

    def pop_max(self) -> Any:
        """Extrae y devuelve el elemento de MAYOR prioridad. O(log n)."""
        if not self._data:
            raise IndexError("pop_max sobre heap vacío")
        return self._pop_at(self._max_index())

    def _pop_at(self, index: int) -> Any:
        last = len(self._data) - 1
        self._swap(index, last)
        _, _, payload = self._data.pop()
        if index < len(self._data):
            self._push_down(index)
            self._push_up(index)
        return payload

    def __len__(self) -> int:
        return len(self._data)

    def is_empty(self) -> bool:
        return not self._data

    def __repr__(self) -> str:  # pragma: no cover
        return f"MinMaxHeap(size={len(self._data)})"
