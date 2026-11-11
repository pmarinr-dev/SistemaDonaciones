"""Estructuras de datos implementadas desde cero para el sistema de donaciones.

Este paquete contiene las cuatro estructuras exigidas por la Fase 3:
    - HashMap            : tabla hash con encadenamiento separado.
    - MinMaxHeap         : montículo min-max (cola de prioridad doble).
    - AVLTree            : árbol binario de búsqueda balanceado (AVL).
    - Graph + dijkstra   : grafo ponderado y caminos mínimos.

Ninguna de ellas delega su lógica interna en `dict`, `heapq` u otras
estructuras equivalentes de la librería estándar: la idea es demostrar
dominio del comportamiento algorítmico y la complejidad asintótica.
"""

from .hash_map import HashMap
from .min_max_heap import MinMaxHeap
from .avl_tree import AVLTree
from .graph import Graph, dijkstra

__all__ = ["HashMap", "MinMaxHeap", "AVLTree", "Graph", "dijkstra"]
