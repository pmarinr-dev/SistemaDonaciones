"""Árbol AVL: árbol binario de búsqueda auto-balanceado.

Mantiene la invariante AVL (factor de balance de cada nodo en {-1, 0, 1})
mediante rotaciones tras cada inserción/eliminación, garantizando altura
O(log n) y por tanto:

Complejidad
-----------
- insert / delete / search : O(log n)
- range_query [lo, hi]     : O(log n + k), k = nº de resultados.
- min / max                : O(log n)

Uso en el dominio
-----------------
Se usa para indexar lotes de ayuda por una clave ordenable (p. ej. la
fecha de caducidad como entero `YYYYMMDD`, o el monto de un aporte
económico) y resolver consultas de rango eficientes, como
"todos los lotes que caducan antes de la fecha X".

El árbol admite claves duplicadas agrupando los valores en una lista por
nodo, de modo que varios lotes pueden compartir la misma fecha.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple


class _Node:
    __slots__ = ("key", "values", "left", "right", "height")

    def __init__(self, key: Any, value: Any) -> None:
        self.key: Any = key
        self.values: List[Any] = [value]
        self.left: Optional["_Node"] = None
        self.right: Optional["_Node"] = None
        self.height: int = 1


class AVLTree:
    """Árbol binario de búsqueda balanceado (AVL)."""

    def __init__(self) -> None:
        self._root: Optional[_Node] = None
        self._size: int = 0

    # ------------------------------------------------------------------ #
    # Helpers de balanceo
    # ------------------------------------------------------------------ #
    @staticmethod
    def _h(node: Optional[_Node]) -> int:
        return node.height if node else 0

    def _balance_factor(self, node: Optional[_Node]) -> int:
        if node is None:
            return 0
        return self._h(node.left) - self._h(node.right)

    def _update_height(self, node: _Node) -> None:
        node.height = 1 + max(self._h(node.left), self._h(node.right))

    def _rotate_right(self, y: _Node) -> _Node:
        x = y.left
        assert x is not None
        t2 = x.right
        x.right = y
        y.left = t2
        self._update_height(y)
        self._update_height(x)
        return x

    def _rotate_left(self, x: _Node) -> _Node:
        y = x.right
        assert y is not None
        t2 = y.left
        y.left = x
        x.right = t2
        self._update_height(x)
        self._update_height(y)
        return y

    def _rebalance(self, node: _Node) -> _Node:
        self._update_height(node)
        balance = self._balance_factor(node)
        # Caso izquierda-izquierda
        if balance > 1 and self._balance_factor(node.left) >= 0:
            return self._rotate_right(node)
        # Caso izquierda-derecha
        if balance > 1 and self._balance_factor(node.left) < 0:
            node.left = self._rotate_left(node.left)  # type: ignore[arg-type]
            return self._rotate_right(node)
        # Caso derecha-derecha
        if balance < -1 and self._balance_factor(node.right) <= 0:
            return self._rotate_left(node)
        # Caso derecha-izquierda
        if balance < -1 and self._balance_factor(node.right) > 0:
            node.right = self._rotate_right(node.right)  # type: ignore[arg-type]
            return self._rotate_left(node)
        return node

    # ------------------------------------------------------------------ #
    # Inserción
    # ------------------------------------------------------------------ #
    def insert(self, key: Any, value: Any) -> None:
        self._root = self._insert(self._root, key, value)

    def _insert(self, node: Optional[_Node], key: Any, value: Any) -> _Node:
        if node is None:
            self._size += 1
            return _Node(key, value)
        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            node.values.append(value)  # clave duplicada
            self._size += 1
            return node
        return self._rebalance(node)

    # ------------------------------------------------------------------ #
    # Búsqueda
    # ------------------------------------------------------------------ #
    def search(self, key: Any) -> List[Any]:
        """Lista de valores asociados a la clave (vacía si no existe)."""
        node = self._root
        while node:
            if key < node.key:
                node = node.left
            elif key > node.key:
                node = node.right
            else:
                return list(node.values)
        return []

    def contains(self, key: Any) -> bool:
        return bool(self.search(key))

    # ------------------------------------------------------------------ #
    # Eliminación
    # ------------------------------------------------------------------ #
    def delete(self, key: Any, value: Any = None, remove_all: bool = False) -> bool:
        """Elimina un valor (o toda la clave) del árbol.

        - Si `remove_all` es True, se elimina el nodo completo con la clave.
        - Si no, se quita únicamente `value` de la lista del nodo; el nodo
          desaparece solo cuando su lista queda vacía.

        Devuelve True si se eliminó algo.
        """
        removed, self._root = self._delete(self._root, key, value, remove_all)
        return removed

    def _min_node(self, node: _Node) -> _Node:
        while node.left:
            node = node.left
        return node

    def _delete(
        self, node: Optional[_Node], key: Any, value: Any, remove_all: bool
    ) -> Tuple[bool, Optional[_Node]]:
        if node is None:
            return False, None
        removed = False
        if key < node.key:
            removed, node.left = self._delete(node.left, key, value, remove_all)
        elif key > node.key:
            removed, node.right = self._delete(node.right, key, value, remove_all)
        else:
            # Nodo encontrado.
            if not remove_all and value is not None and value in node.values:
                node.values.remove(value)
                self._size -= 1
                if node.values:
                    return True, node  # el nodo permanece
                removed = True
            else:
                removed = True
                self._size -= len(node.values)

            # Eliminar el nodo (lista vacía o remove_all).
            if node.left is None:
                return removed, node.right
            if node.right is None:
                return removed, node.left
            successor = self._min_node(node.right)
            node.key, node.values = successor.key, successor.values
            # El sucesor NO desaparece del árbol: sus valores suben a este
            # nodo. La eliminación recursiva del sucesor volverá a restar su
            # conteo de `_size`, así que lo compensamos por adelantado.
            self._size += len(successor.values)
            _, node.right = self._delete(
                node.right, successor.key, None, remove_all=True
            )
        if node is None:
            return removed, None
        return removed, self._rebalance(node)

    # ------------------------------------------------------------------ #
    # Consultas de rango y extremos
    # ------------------------------------------------------------------ #
    def range_query(self, low: Any, high: Any) -> List[Tuple[Any, Any]]:
        """Pares (clave, valor) con low <= clave <= high, en orden ascendente."""
        result: List[Tuple[Any, Any]] = []
        self._range(self._root, low, high, result)
        return result

    def _range(
        self, node: Optional[_Node], low: Any, high: Any, out: List[Tuple[Any, Any]]
    ) -> None:
        if node is None:
            return
        if low < node.key:
            self._range(node.left, low, high, out)
        if low <= node.key <= high:
            for v in node.values:
                out.append((node.key, v))
        if node.key < high:
            self._range(node.right, low, high, out)

    def min_key(self) -> Optional[Any]:
        if self._root is None:
            return None
        return self._min_node(self._root).key

    def max_key(self) -> Optional[Any]:
        if self._root is None:
            return None
        node = self._root
        while node.right:
            node = node.right
        return node.key

    def in_order(self) -> List[Tuple[Any, Any]]:
        """Todos los pares (clave, valor) en orden ascendente de clave."""
        result: List[Tuple[Any, Any]] = []
        self._in_order(self._root, result)
        return result

    def _in_order(self, node: Optional[_Node], out: List[Tuple[Any, Any]]) -> None:
        if node is None:
            return
        self._in_order(node.left, out)
        for v in node.values:
            out.append((node.key, v))
        self._in_order(node.right, out)

    @property
    def height(self) -> int:
        return self._h(self._root)

    def __len__(self) -> int:
        return self._size

    def __repr__(self) -> str:  # pragma: no cover
        return f"AVLTree(size={self._size}, height={self.height})"
