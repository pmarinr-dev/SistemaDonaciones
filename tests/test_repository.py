"""Pruebas de persistencia: parsing robusto ante registros nulos/corruptos."""

import json

from sistema_donaciones.core import DataRepository


def _escribir(tmp_path, data):
    p = tmp_path / "datos.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_carga_valida(tmp_path):
    data = {
        "donantes": [{"id": "D1", "nombre": "Cruz Roja", "tipo": "ong"}],
        "lotes": [],
        "centros": [],
        "municipios": [],
    }
    res = DataRepository.load_json(_escribir(tmp_path, data))
    assert len(res.donantes) == 1
    assert res.errores == []


def test_registro_nulo_se_omite(tmp_path):
    data = {"donantes": [None, {"id": "D1", "nombre": "X", "tipo": "ong"}]}
    res = DataRepository.load_json(_escribir(tmp_path, data))
    assert len(res.donantes) == 1
    assert any("nulo" in e for e in res.errores)


def test_registro_mal_estructurado_no_aborta_carga(tmp_path):
    data = {
        "lotes": [
            {"id": "L1"},  # faltan campos obligatorios
            {
                "id": "L2",
                "categoria": "agua",
                "descripcion": "ok",
                "cantidad": 5,
                "peso_kg": 1,
                "volumen_m3": 1,
                "requiere_frio": False,
                "fecha_caducidad": "2026-12-01",
                "donante_id": "D1",
            },
        ]
    }
    res = DataRepository.load_json(_escribir(tmp_path, data))
    assert len(res.lotes) == 1  # el válido se cargó
    assert len(res.errores) == 1  # el inválido se reportó


def test_cantidad_negativa_reportada(tmp_path):
    data = {
        "lotes": [
            {
                "id": "L1",
                "categoria": "agua",
                "descripcion": "mal",
                "cantidad": -10,
                "peso_kg": 1,
                "volumen_m3": 1,
                "requiere_frio": False,
                "fecha_caducidad": "2026-12-01",
                "donante_id": "D1",
            }
        ]
    }
    res = DataRepository.load_json(_escribir(tmp_path, data))
    assert len(res.lotes) == 0
    assert len(res.errores) == 1


def test_archivo_inexistente(tmp_path):
    res = DataRepository.load_json(tmp_path / "no_existe.json")
    assert any("no encontrado" in e.lower() for e in res.errores)


def test_json_corrupto(tmp_path):
    p = tmp_path / "corrupto.json"
    p.write_text("{ esto no es json ]", encoding="utf-8")
    res = DataRepository.load_json(p)
    assert any("inválido" in e.lower() for e in res.errores)


def test_guardar_y_recargar(tmp_path):
    data = {
        "donantes": [{"id": "D1", "nombre": "X", "tipo": "ong"}],
        "municipios": [
            {
                "id": "M1",
                "nombre": "Mocoa",
                "departamento": "Putumayo",
                "nivel_urgencia": 4,
                "poblacion": 100,
                "necesidades": {"agua": 10},
            }
        ],
    }
    res = DataRepository.load_json(_escribir(tmp_path, data))
    out = tmp_path / "out.json"
    DataRepository.save_json(out, res)
    recargado = DataRepository.load_json(out)
    assert len(recargado.donantes) == 1
    assert len(recargado.municipios) == 1
