# Sistema Integral de Gestión y Distribución de Donaciones Post-Desastre

Universidad EAFIT · Estructuras de Datos y Algoritmos · Evaluación Práctica 3

Software para coordinar la recepción, trazabilidad, priorización y despacho de
ayuda humanitaria tras un evento sísmico en Colombia. Implementa **desde cero**
las cuatro estructuras de datos exigidas (tabla hash, min-max heap, árbol AVL y
grafo con Dijkstra), una capa de negocio, una interfaz gráfica Tkinter y una
suite de pruebas automatizadas.

## Estructura del proyecto

```
SistemaDonaciones/
├── src/sistema_donaciones/
│   ├── structures/        # Estructuras de datos a mano (Fase 3)
│   │   ├── hash_map.py        # Tabla hash (encadenamiento separado)
│   │   ├── min_max_heap.py    # Cola de prioridad doble
│   │   ├── avl_tree.py        # Árbol binario balanceado AVL
│   │   └── graph.py           # Grafo ponderado + Dijkstra
│   ├── models/            # Entidades del dominio (Fase 1)
│   │   ├── enums.py
│   │   └── entities.py        # Donante, LoteAyuda, CentroAcopio, Municipio
│   ├── core/              # Lógica de negocio y persistencia (Fase 2)
│   │   ├── repository.py      # (de)serialización JSON/CSV robusta
│   │   ├── system.py          # Fachada SistemaDonaciones
│   │   └── loader.py          # Construcción del sistema desde JSON
│   ├── gui/
│   │   └── app.py             # Panel de control Tkinter (Fase 4)
│   └── __main__.py        # CLI: demo por consola o --gui
├── data/datos_colombia.json   # Datos sintéticos del contexto colombiano
├── tests/                 # 72 pruebas (unitarias + bordes + benchmark)
└── docs/INFORME.md        # Memoria, análisis Big-O y anexo de IA
```

## Requisitos

- Python 3.10+ (probado en 3.11).
- `tkinter` (incluido con Python estándar) para la GUI.
- `pytest` para las pruebas.

## Ejecución

```bash
# Demo por consola (carga datos, asigna recursos, muestra informes)
PYTHONPATH=src python3 -m sistema_donaciones

# Interfaz gráfica
PYTHONPATH=src python3 -m sistema_donaciones --gui

# Con un archivo de datos propio
PYTHONPATH=src python3 -m sistema_donaciones --data mis_datos.json
```

## Pruebas

```bash
PYTHONPATH=src python3 -m pytest            # todas (72)
PYTHONPATH=src python3 -m pytest -m "not benchmark"   # omitir benchmarks
PYTHONPATH=src python3 -m pytest tests/test_benchmark.py -s   # ver tiempos
```

## Las cuatro estructuras y su rol

| Estructura | Archivo | Uso en el dominio | Complejidad clave |
|------------|---------|-------------------|-------------------|
| **Hash Map** | `hash_map.py` | Índices O(1) de donantes, centros, municipios y lotes | get/set/delete O(1) amortizado |
| **Min-Max Heap** | `min_max_heap.py` | Triaje: extraer el municipio más urgente | push/pop O(log n), peek O(1) |
| **Árbol AVL** | `avl_tree.py` | Lotes ordenados por caducidad; consultas de rango (FEFO) | insert/search/range O(log n) |
| **Grafo + Dijkstra** | `graph.py` | Red vial; rutas de despacho de costo mínimo | O((V+E) log V) |

Ninguna de ellas delega su lógica en `dict`, `heapq` u otras estructuras
equivalentes de la librería estándar. El análisis asintótico detallado y el
anexo de transparencia de IA están en [`docs/INFORME.md`](docs/INFORME.md).
