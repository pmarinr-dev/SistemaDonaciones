"""Tabla hash con encadenamiento separado (separate chaining).

Diseño
------
- Arreglo de "buckets"; cada bucket es una lista de pares (clave, valor).
- La posición se calcula con `hash(clave) % capacidad`.
- Se mantiene un factor de carga objetivo; al superarlo se duplica la
  capacidad y se re-hashean todos los elementos (amortización).

Complejidad
-----------
- get / set / delete : O(1) amortizado (O(n) en el peor caso patológico
  cuando todas las claves colisionan en el mismo bucket).
- Redimensionado      : O(n) puntual, amortizado a O(1) por inserción.

Se eligió encadenamiento separado (en lugar de direccionamiento abierto)
porque simplifica el borrado y degrada de forma más predecible ante
factores de carga altos, algo deseable en un sistema que recibe ráfagas
masivas de donaciones.
"""

from __future__ import annotations

from typing import Any, Iterator, List, Optional, Tuple

_MISSING = object()


class HashMap:
    """Mapa hash genérico clave -> valor."""

    _INITIAL_CAPACITY = 16
    _MAX_LOAD_FACTOR = 0.75
    _MIN_LOAD_FACTOR = 0.20  # para reducir capacidad tras borrados masivos

    def __init__(self, capacity: int = _INITIAL_CAPACITY) -> None:
        if capacity < 1:
            raise ValueError("La capacidad inicial debe ser >= 1")
        self._capacity: int = capacity
        self._size: int = 0
        self._buckets: List[List[Tuple[Any, Any]]] = [[] for _ in range(capacity)]

    # ------------------------------------------------------------------ #
    # Utilidades internas
    # ------------------------------------------------------------------ #
    def _index(self, key: Any) -> int:
        """Índice de bucket para la clave dada."""
        return hash(key) % self._capacity

    def _resize(self, new_capacity: int) -> None:
        """Re-hashea todos los pares hacia una tabla de nueva capacidad."""
        old_items = list(self.items())
        self._capacity = max(new_capacity, self._INITIAL_CAPACITY)
        self._buckets = [[] for _ in range(self._capacity)]
        self._size = 0
        for key, value in old_items:
            self.set(key, value)

    @property
    def load_factor(self) -> float:
        return self._size / self._capacity

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def set(self, key: Any, value: Any) -> None:
        """Inserta o actualiza el valor asociado a `key`."""
        bucket = self._buckets[self._index(key)]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
        self._size += 1
        if self.load_factor > self._MAX_LOAD_FACTOR:
            self._resize(self._capacity * 2)

    def get(self, key: Any, default: Any = _MISSING) -> Any:
        """Devuelve el valor de `key`. Lanza KeyError si no existe y no hay default."""
        bucket = self._buckets[self._index(key)]
        for k, v in bucket:
            if k == key:
                return v
        if default is _MISSING:
            raise KeyError(key)
        return default

    def delete(self, key: Any) -> None:
        """Elimina `key`. Lanza KeyError si no existe."""
        bucket = self._buckets[self._index(key)]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                del bucket[i]
                self._size -= 1
                if (
                    self._capacity > self._INITIAL_CAPACITY
                    and self.load_factor < self._MIN_LOAD_FACTOR
                ):
                    self._resize(self._capacity // 2)
                return
        raise KeyError(key)

    def contains(self, key: Any) -> bool:
        bucket = self._buckets[self._index(key)]
        return any(k == key for k, _ in bucket)

    def keys(self) -> Iterator[Any]:
        for bucket in self._buckets:
            for k, _ in bucket:
                yield k

    def values(self) -> Iterator[Any]:
        for bucket in self._buckets:
            for _, v in bucket:
                yield v

    def items(self) -> Iterator[Tuple[Any, Any]]:
        for bucket in self._buckets:
            for pair in bucket:
                yield pair

    # ------------------------------------------------------------------ #
    # Protocolos de Python para ergonomía (azúcar sintáctico)
    # ------------------------------------------------------------------ #
    def __setitem__(self, key: Any, value: Any) -> None:
        self.set(key, value)

    def __getitem__(self, key: Any) -> Any:
        return self.get(key)

    def __delitem__(self, key: Any) -> None:
        self.delete(key)

    def __contains__(self, key: Any) -> bool:
        return self.contains(key)

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[Any]:
        return self.keys()

    def __repr__(self) -> str:  # pragma: no cover - solo representación
        return f"HashMap(size={self._size}, capacity={self._capacity})"
