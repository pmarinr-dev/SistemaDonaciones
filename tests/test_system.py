"""Pruebas de la lógica de negocio (Fase 2)."""

import datetime

import pytest

from sistema_donaciones.core import SistemaDonaciones
from sistema_donaciones.models import (
    CategoriaAyuda,
    CentroAcopio,
    Donante,
    EstadoLote,
    LoteAyuda,
    Municipio,
)


def _sistema_basico() -> SistemaDonaciones:
    s = SistemaDonaciones()
    s.registrar_donante(Donante(id="D1", nombre="Cruz Roja", tipo="ong"))
    s.registrar_centro(
        CentroAcopio(id="C1", nombre="Acopio", ciudad="Bogota", capacidad_m3=100)
    )
    s.registrar_municipio(
        Municipio(
            id="M1",
            nombre="Mocoa",
            departamento="Putumayo",
            nivel_urgencia=4,
            poblacion=1000,
            necesidades={"agua": 100},
        )
    )
    s.registrar_municipio(
        Municipio(
            id="M2",
            nombre="Leticia",
            departamento="Amazonas",
            nivel_urgencia=2,
            poblacion=500,
            necesidades={"agua": 100},
        )
    )
    return s


def _lote(id_, cat, cant, fecha, donante="D1"):
    return LoteAyuda(
        id=id_,
        categoria=cat,
        descripcion="x",
        cantidad=cant,
        peso_kg=1,
        volumen_m3=1,
        requiere_frio=False,
        fecha_caducidad=fecha,
        donante_id=donante,
    )


def test_registrar_donacion_donante_inexistente_falla():
    s = SistemaDonaciones()
    with pytest.raises(ValueError):
        s.registrar_donacion(_lote("L1", "agua", 10, "2026-12-01"))


def test_registrar_donacion_duplicada_falla():
    s = _sistema_basico()
    s.registrar_donacion(_lote("L1", "agua", 10, "2026-12-01"))
    with pytest.raises(ValueError):
        s.registrar_donacion(_lote("L1", "agua", 5, "2026-12-01"))


def test_busqueda_por_id():
    s = _sistema_basico()
    s.registrar_donacion(_lote("L1", "agua", 10, "2026-12-01"))
    assert s.buscar_lote("L1").cantidad == 10
    assert s.buscar_lote("NOPE") is None


def test_busqueda_por_categoria():
    s = _sistema_basico()
    s.registrar_donacion(_lote("L1", "agua", 10, "2026-12-01"))
    s.registrar_donacion(_lote("L2", "medico", 5, "2026-12-01"))
    aguas = s.buscar_por_categoria(CategoriaAyuda.AGUA)
    assert [l.id for l in aguas] == ["L1"]


def test_proximos_a_caducar_rango():
    s = _sistema_basico()
    s.registrar_donacion(_lote("L1", "agua", 10, "2026-02-01"))  # pronto
    s.registrar_donacion(_lote("L2", "agua", 10, "2027-01-01"))  # lejos
    ref = datetime.date(2026, 1, 15)
    proximos = s.buscar_proximos_a_caducar(30, referencia=ref)
    assert [l.id for l in proximos] == ["L1"]


def test_asignacion_prioriza_municipio_mas_urgente():
    # Solo hay 100 de agua; M1 (urgencia 4) debe servirse antes que M2 (2).
    s = _sistema_basico()
    s.registrar_donacion(_lote("L1", "agua", 100, "2026-12-01"))
    asignaciones = s.asignar_recursos()
    primero = asignaciones[0]
    assert primero.municipio_id == "M1"


def test_asignacion_fefo_prioriza_caducidad_proxima():
    # Dos lotes de agua; el que caduca antes debe asignarse primero.
    s = _sistema_basico()
    s.registrar_donacion(_lote("L_tarde", "agua", 100, "2027-01-01"))
    s.registrar_donacion(_lote("L_pronto", "agua", 100, "2026-03-01"))
    asignaciones = s.asignar_recursos()
    # El primer lote asignado (a M1, el más urgente) es el que caduca antes.
    assert asignaciones[0].lote_id == "L_pronto"


def test_lote_asignado_no_queda_disponible():
    # Regla de negocio explícita de la rúbrica.
    s = _sistema_basico()
    s.registrar_donacion(_lote("L1", "agua", 100, "2026-12-01"))
    s.asignar_recursos()
    lote = s.buscar_lote("L1")
    assert lote.estado is EstadoLote.ASIGNADO
    assert not lote.esta_disponible()
    # Ya no aparece como disponible en búsquedas.
    assert s.buscar_por_categoria(CategoriaAyuda.AGUA, solo_disponibles=True) == []


def test_despachar_flujo_de_estados():
    s = _sistema_basico()
    s.registrar_donacion(_lote("L1", "agua", 100, "2026-12-01"))
    s.asignar_recursos()
    s.despachar("L1")
    assert s.buscar_lote("L1").estado is EstadoLote.DESPACHADO


def test_despachar_lote_no_asignado_falla():
    s = _sistema_basico()
    s.registrar_donacion(_lote("L1", "agua", 100, "2026-12-01"))
    with pytest.raises(ValueError):
        s.despachar("L1")  # está DISPONIBLE, no ASIGNADO


def test_alertas_desabastecimiento():
    s = _sistema_basico()  # demanda agua = 200 total
    s.registrar_donacion(_lote("L1", "agua", 50, "2026-12-01"))
    alertas = s.alertas_desabastecimiento()
    agua = next(a for a in alertas if a["categoria"] == "agua")
    assert agua["deficit"] == 150  # 200 demanda - 50 disponible


def test_balance_consistente_tras_transacciones():
    s = _sistema_basico()
    s.registrar_donacion(_lote("L1", "agua", 100, "2026-12-01"))
    s.registrar_donacion(_lote("L2", "agua", 100, "2026-12-01"))
    s.asignar_recursos()
    s.despachar("L1")
    balance = s.balance_stock()["agua"]
    # 200 totales conservados entre estados.
    assert balance["disponible"] + balance["asignado"] + balance["despachado"] == 200


def test_marcar_vencidos():
    s = _sistema_basico()
    s.registrar_donacion(_lote("L1", "agua", 10, "2026-02-01"))
    vencidos = s.marcar_vencidos(referencia=datetime.date(2026, 6, 1))
    assert "L1" in vencidos
    assert s.buscar_lote("L1").estado is EstadoLote.VENCIDO


def test_ruta_optima_integra_dijkstra():
    s = _sistema_basico()
    s.agregar_ruta("C1", "M1", 50)
    ruta, costo = s.ruta_optima("C1", "M1")
    assert ruta == ["C1", "M1"]
    assert costo == 50
