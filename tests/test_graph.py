"""Pruebas del grafo y Dijkstra."""

import pytest

from sistema_donaciones.structures import Graph, dijkstra
from sistema_donaciones.structures.graph import shortest_path


def _grafo_ejemplo() -> Graph:
    g = Graph(directed=False)
    g.add_edge("A", "B", 1)
    g.add_edge("B", "C", 2)
    g.add_edge("A", "C", 10)
    g.add_edge("C", "D", 1)
    return g


def test_vertices_y_aristas():
    g = _grafo_ejemplo()
    assert set(g.vertices()) == {"A", "B", "C", "D"}
    assert g.edge_weight("A", "B") == 1
    assert g.edge_weight("B", "A") == 1  # no dirigido


def test_dijkstra_distancias():
    g = _grafo_ejemplo()
    dist, _ = dijkstra(g, "A")
    assert dist["A"] == 0
    assert dist["B"] == 1
    assert dist["C"] == 3   # A-B-C (1+2) mejor que A-C (10)
    assert dist["D"] == 4   # A-B-C-D


def test_shortest_path_reconstruye_ruta():
    g = _grafo_ejemplo()
    ruta, costo = shortest_path(g, "A", "D")
    assert ruta == ["A", "B", "C", "D"]
    assert costo == 4


def test_nodo_inalcanzable():
    g = Graph()
    g.add_edge("A", "B", 1)
    g.add_vertex("Z")  # aislado
    ruta, costo = shortest_path(g, "A", "Z")
    assert ruta == []
    assert costo == float("inf")


def test_peso_negativo_rechazado():
    g = Graph()
    with pytest.raises(ValueError):
        g.add_edge("A", "B", -5)


def test_origen_inexistente():
    g = _grafo_ejemplo()
    with pytest.raises(KeyError):
        dijkstra(g, "NOPE")


def test_grafo_dirigido():
    g = Graph(directed=True)
    g.add_edge("A", "B", 1)
    assert g.edge_weight("A", "B") == 1
    assert g.edge_weight("B", "A") is None
