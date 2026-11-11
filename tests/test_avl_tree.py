"""Pruebas del árbol AVL (balanceo, rango, duplicados, borrado)."""

import math
import random

from sistema_donaciones.structures import AVLTree


def _es_balanceado(arbol: AVLTree) -> bool:
    def check(node):
        if node is None:
            return 0, True
        hl, bl = check(node.left)
        hr, br = check(node.right)
        balanceado = bl and br and abs(hl - hr) <= 1
        return 1 + max(hl, hr), balanceado

    _, ok = check(arbol._root)
    return ok


def test_insert_search():
    t = AVLTree()
    t.insert(10, "a")
    t.insert(5, "b")
    t.insert(15, "c")
    assert t.search(10) == ["a"]
    assert t.search(5) == ["b"]
    assert t.search(999) == []


def test_in_order_ordenado():
    t = AVLTree()
    for k in [50, 20, 70, 10, 30, 60, 80]:
        t.insert(k, str(k))
    claves = [k for k, _ in t.in_order()]
    assert claves == sorted(claves)


def test_balanceo_tras_inserciones_ordenadas():
    # Inserción monotónica: sin balanceo sería una lista enlazada.
    t = AVLTree()
    n = 1000
    for i in range(n):
        t.insert(i, i)
    assert _es_balanceado(t)
    # altura ~ log2(n); con margen AVL < 1.45*log2(n+2)
    assert t.height <= 1.45 * math.log2(n + 2)


def test_range_query():
    t = AVLTree()
    for k in range(0, 100, 5):
        t.insert(k, k)
    res = t.range_query(20, 40)
    claves = [k for k, _ in res]
    assert claves == [20, 25, 30, 35, 40]


def test_claves_duplicadas():
    t = AVLTree()
    t.insert(10, "x")
    t.insert(10, "y")
    t.insert(10, "z")
    assert sorted(t.search(10)) == ["x", "y", "z"]
    assert len(t) == 3


def test_delete_valor_especifico():
    t = AVLTree()
    t.insert(10, "x")
    t.insert(10, "y")
    assert t.delete(10, "x") is True
    assert t.search(10) == ["y"]
    assert t.contains(10)


def test_delete_nodo_completo_mantiene_balance():
    t = AVLTree()
    datos = list(range(200))
    random.shuffle(datos)
    for k in datos:
        t.insert(k, k)
    for k in random.sample(datos, 100):
        t.delete(k, remove_all=True)
    assert _es_balanceado(t)
    assert len(t) == 100


def test_min_max_key():
    t = AVLTree()
    for k in [42, 7, 99, 13]:
        t.insert(k, k)
    assert t.min_key() == 7
    assert t.max_key() == 99


def test_arbol_vacio():
    t = AVLTree()
    assert t.min_key() is None
    assert t.max_key() is None
    assert t.in_order() == []
    assert t.delete(1) is False
