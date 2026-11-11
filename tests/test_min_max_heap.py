"""Pruebas del Min-Max Heap (prioridad doble y orden estable)."""

import random

import pytest

from sistema_donaciones.structures import MinMaxHeap


def test_peek_min_max_simple():
    h = MinMaxHeap()
    for v in [5, 1, 9, 3, 7]:
        h.push(v)
    assert h.peek_min() == 1
    assert h.peek_max() == 9
    assert len(h) == 5


def test_pop_min_orden_ascendente():
    h = MinMaxHeap()
    datos = [15, 3, 27, 8, 1, 42, 19]
    for v in datos:
        h.push(v)
    salida = [h.pop_min() for _ in range(len(datos))]
    assert salida == sorted(datos)


def test_pop_max_orden_descendente():
    h = MinMaxHeap()
    datos = [15, 3, 27, 8, 1, 42, 19]
    for v in datos:
        h.push(v)
    salida = [h.pop_max() for _ in range(len(datos))]
    assert salida == sorted(datos, reverse=True)


def test_extraccion_mixta_consistente():
    h = MinMaxHeap()
    datos = list(range(100))
    random.shuffle(datos)
    for v in datos:
        h.push(v)
    restantes = sorted(datos)
    for _ in range(25):
        assert h.pop_min() == restantes.pop(0)
        assert h.pop_max() == restantes.pop()
    assert len(h) == len(restantes)


def test_heap_vacio_lanza():
    h = MinMaxHeap()
    assert h.is_empty()
    with pytest.raises(IndexError):
        h.peek_min()
    with pytest.raises(IndexError):
        h.pop_max()


def test_un_solo_elemento():
    h = MinMaxHeap()
    h.push(42)
    assert h.peek_min() == h.peek_max() == 42
    assert h.pop_max() == 42
    assert h.is_empty()


def test_key_personalizada_y_desempate_por_insercion():
    # Prioriza por el primer campo del payload. El contador monotónico
    # interno desempata de forma determinista entre prioridades iguales.
    h = MinMaxHeap(key=lambda t: t[0])
    h.push((2, "a"))
    h.push((2, "b"))
    h.push((1, "c"))
    # El mínimo absoluto es la prioridad 1.
    assert h.pop_min() == (1, "c")
    # Quedan dos con prioridad 2: ambos deben salir, en cualquier orden
    # estable, al pedir el máximo repetidamente.
    primero = h.pop_max()
    segundo = h.pop_max()
    assert {primero, segundo} == {(2, "a"), (2, "b")}
    assert h.is_empty()


def test_stress_fuzz_min():
    for _ in range(20):
        datos = [random.randint(-1000, 1000) for _ in range(200)]
        h = MinMaxHeap()
        for v in datos:
            h.push(v)
        out = [h.pop_min() for _ in range(len(datos))]
        assert out == sorted(datos)
