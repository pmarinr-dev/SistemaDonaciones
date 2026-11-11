"""Benchmarking: estructuras elegidas vs. alternativas ingenuas (Fase 3).

Estas pruebas NO validan corrección (eso lo hacen los demás tests), sino
que evidencian empíricamente la diferencia de complejidad asintótica:

    - MinMaxHeap (O(log n) por extracción del máximo) vs. lista lineal
      que busca el máximo con O(n) cada vez.
    - AVLTree (consulta de rango O(log n + k)) vs. lista no ordenada que
      filtra en O(n).

Se marcan con @pytest.mark.benchmark para poder excluirlas en CI rápida:
    pytest -m "not benchmark"     # omite benchmarks
    pytest tests/test_benchmark.py -s   # ver tiempos impresos
"""

import random
import time

import pytest

from sistema_donaciones.structures import AVLTree, MinMaxHeap

pytestmark = pytest.mark.benchmark


def _cronometrar(fn) -> float:
    inicio = time.perf_counter()
    fn()
    return time.perf_counter() - inicio


def test_heap_vs_lista_lineal_extraccion_maximos():
    n = 20_000
    datos = [random.random() for _ in range(n)]

    # Alternativa ingenua: lista + max()/remove() repetido => O(n^2).
    def ingenua():
        lista = list(datos)
        for _ in range(500):
            m = max(lista)
            lista.remove(m)

    # Estructura elegida: min-max heap => O(log n) por extracción.
    def con_heap():
        h = MinMaxHeap()
        for v in datos:
            h.push(v)
        for _ in range(500):
            h.pop_max()

    t_ingenua = _cronometrar(ingenua)
    t_heap = _cronometrar(con_heap)
    print(f"\n[heap] lista lineal: {t_ingenua:.4f}s | min-max heap: {t_heap:.4f}s")

    # Para 500 extracciones sobre 20k elementos, el heap debe ganar
    # (incluyendo el costo de construcción). Umbral conservador.
    assert t_heap < t_ingenua


def test_avl_vs_lista_consulta_rango():
    n = 50_000
    claves = random.sample(range(n * 4), n)

    arbol = AVLTree()
    for k in claves:
        arbol.insert(k, k)
    lista = list(claves)

    lo, hi = n, n + 1000

    def rango_avl():
        for _ in range(200):
            arbol.range_query(lo, hi)

    def rango_lista():
        for _ in range(200):
            [x for x in lista if lo <= x <= hi]  # O(n) por consulta

    t_avl = _cronometrar(rango_avl)
    t_lista = _cronometrar(rango_lista)
    print(f"\n[avl] lista O(n): {t_lista:.4f}s | AVL O(log n + k): {t_avl:.4f}s")

    assert t_avl < t_lista
