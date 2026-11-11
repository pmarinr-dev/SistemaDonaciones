"""Pruebas del HashMap (incluye casos de borde y redimensionado)."""

import pytest

from sistema_donaciones.structures import HashMap


def test_set_get_basico():
    h = HashMap()
    h.set("a", 1)
    h.set("b", 2)
    assert h.get("a") == 1
    assert h.get("b") == 2
    assert len(h) == 2


def test_actualizacion_no_incrementa_tamano():
    h = HashMap()
    h.set("k", 1)
    h.set("k", 2)
    assert h.get("k") == 2
    assert len(h) == 1


def test_get_default_y_keyerror():
    h = HashMap()
    assert h.get("x", None) is None
    with pytest.raises(KeyError):
        h.get("x")


def test_delete_y_keyerror():
    h = HashMap()
    h.set("k", 1)
    h.delete("k")
    assert "k" not in h
    with pytest.raises(KeyError):
        h.delete("k")


def test_redimensionado_preserva_datos():
    h = HashMap(capacity=2)
    for i in range(200):
        h.set(i, i * i)
    assert len(h) == 200
    for i in range(200):
        assert h.get(i) == i * i
    # tras tantas inserciones la capacidad debe haber crecido
    assert h._capacity > 2


def test_contraccion_tras_borrados():
    h = HashMap(capacity=16)
    for i in range(300):
        h.set(i, i)
    cap_grande = h._capacity
    for i in range(300):
        h.delete(i)
    assert len(h) == 0
    assert h._capacity < cap_grande


def test_iteracion_items_keys_values():
    h = HashMap()
    datos = {"x": 1, "y": 2, "z": 3}
    for k, v in datos.items():
        h.set(k, v)
    assert dict(h.items()) == datos
    assert set(h.keys()) == set(datos)
    assert sorted(h.values()) == [1, 2, 3]


def test_azucar_sintactico():
    h = HashMap()
    h["a"] = 10
    assert h["a"] == 10
    assert "a" in h
    del h["a"]
    assert "a" not in h


def test_colisiones_misma_clave_logica():
    # Fuerza colisiones con capacidad mínima y verifica integridad.
    h = HashMap(capacity=1)
    for i in range(50):
        h.set(f"key{i}", i)
    for i in range(50):
        assert h.get(f"key{i}") == i
