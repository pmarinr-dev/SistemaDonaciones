"""Pruebas de modelos: validación de tipos, rangos y coherencia temporal."""

import pytest

from sistema_donaciones.models import (
    CategoriaAyuda,
    CentroAcopio,
    Donante,
    EstadoLote,
    LoteAyuda,
    Municipio,
    NivelUrgencia,
)


# --- Donante ------------------------------------------------------------- #
def test_donante_valido_y_inmutable():
    d = Donante(id="D1", nombre="Cruz Roja", tipo="ong")
    assert d.id == "D1"
    with pytest.raises(Exception):  # frozen dataclass => FrozenInstanceError
        d.nombre = "otro"


def test_donante_id_vacio_falla():
    with pytest.raises(ValueError):
        Donante(id="", nombre="X", tipo="ong")


# --- LoteAyuda ----------------------------------------------------------- #
def _lote_base(**kw):
    datos = dict(
        id="L1",
        categoria="medico",
        descripcion="kit",
        cantidad=10,
        peso_kg=5.0,
        volumen_m3=1.0,
        requiere_frio=False,
        fecha_caducidad="2026-12-31",
        donante_id="D1",
    )
    datos.update(kw)
    return LoteAyuda(**datos)


def test_lote_valido():
    l = _lote_base()
    assert l.categoria is CategoriaAyuda.MEDICO
    assert l.estado is EstadoLote.DISPONIBLE
    assert l.esta_disponible()


def test_lote_cantidad_negativa_falla():
    with pytest.raises(ValueError):
        _lote_base(cantidad=-1)


def test_lote_peso_negativo_falla():
    with pytest.raises(ValueError):
        _lote_base(peso_kg=-0.5)


def test_lote_caducidad_anterior_al_evento_falla():
    # EVENTO_FECHA = 2026-01-15; una fecha previa debe fallar.
    with pytest.raises(ValueError):
        _lote_base(fecha_caducidad="2025-01-01")


def test_fondos_no_restringen_caducidad():
    # Los fondos no caducan: se permite fecha igual al evento.
    l = _lote_base(categoria="fondos", fecha_caducidad="2026-01-15")
    assert l.categoria is CategoriaAyuda.FONDOS


def test_fecha_invalida_falla():
    with pytest.raises(ValueError):
        _lote_base(fecha_caducidad="no-es-fecha")


def test_clave_caducidad():
    l = _lote_base(fecha_caducidad="2026-07-04")
    assert l.clave_caducidad() == 20260704


# --- Municipio ----------------------------------------------------------- #
def test_municipio_valido():
    m = Municipio(
        id="M1",
        nombre="Mocoa",
        departamento="Putumayo",
        nivel_urgencia=4,
        poblacion=45000,
        necesidades={"medico": 100, "agua": 50},
    )
    assert m.nivel_urgencia is NivelUrgencia.CRITICA
    assert m.necesidad_total() == 150


def test_municipio_necesidad_negativa_falla():
    with pytest.raises(ValueError):
        Municipio(
            id="M1",
            nombre="X",
            departamento="Y",
            nivel_urgencia=2,
            poblacion=100,
            necesidades={"agua": -5},
        )


def test_municipio_categoria_invalida_falla():
    with pytest.raises(ValueError):
        Municipio(
            id="M1",
            nombre="X",
            departamento="Y",
            nivel_urgencia=2,
            poblacion=100,
            necesidades={"inexistente": 5},
        )


def test_nivel_urgencia_desde_string():
    m = Municipio(
        id="M1", nombre="X", departamento="Y", nivel_urgencia="ALTA", poblacion=10
    )
    assert m.nivel_urgencia is NivelUrgencia.ALTA


# --- CentroAcopio -------------------------------------------------------- #
def test_centro_capacidad_negativa_falla():
    with pytest.raises(ValueError):
        CentroAcopio(id="C1", nombre="X", ciudad="Bogota", capacidad_m3=-1)


# --- Round-trip de serialización ---------------------------------------- #
def test_roundtrip_lote():
    l = _lote_base()
    assert LoteAyuda.from_dict(l.to_dict()).to_dict() == l.to_dict()


def test_roundtrip_municipio():
    m = Municipio(
        id="M1",
        nombre="Mocoa",
        departamento="Putumayo",
        nivel_urgencia=4,
        poblacion=45000,
        necesidades={"medico": 100},
    )
    assert Municipio.from_dict(m.to_dict()).to_dict() == m.to_dict()
