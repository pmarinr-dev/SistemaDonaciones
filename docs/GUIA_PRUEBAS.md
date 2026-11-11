# Guía paso a paso para probar el sistema

Esta guía explica cómo ejecutar y probar el proyecto, incluida la interfaz
gráfica. Está pensada para correrse en **tu computador local** (la GUI necesita
una pantalla de escritorio).

---

## Paso 0 — Requisitos previos

- **Python 3.10 o superior** (el proyecto se desarrolló y probó con 3.11).
  Verifícalo con:
  ```bash
  python3 --version
  ```
- **Tkinter** (viene incluido con Python en la mayoría de instalaciones).
  Compruébalo con:
  ```bash
  python3 -c "import tkinter; print('Tkinter OK', tkinter.TkVersion)"
  ```
  - En **Windows** y **macOS** (instalador oficial de python.org) ya viene incluido.
  - En **Linux (Debian/Ubuntu)** si falta: `sudo apt install python3-tk`
  - En **Linux (Fedora)**: `sudo dnf install python3-tkinter`
- **pytest** (solo para las pruebas automatizadas):
  ```bash
  pip install pytest
  ```

---

## Paso 1 — Obtener el código

Si aún no lo tienes clonado:

```bash
git clone https://github.com/pmarinr-dev/SistemaDonaciones.git
cd SistemaDonaciones
```

Si el trabajo todavía está en la rama del PR (no fusionado a `main`):

```bash
git checkout feature/sistema-donaciones
```

> **Nota sobre `PYTHONPATH`**: el código vive en la carpeta `src/`, por eso todos
> los comandos anteponen `PYTHONPATH=src`. Esto le dice a Python dónde encontrar
> el paquete `sistema_donaciones`.
>
> - **Linux / macOS**: `PYTHONPATH=src python3 -m ...`
> - **Windows (PowerShell)**: ejecuta primero `$env:PYTHONPATH="src"` y luego
>   `python -m ...`
> - **Windows (CMD)**: `set PYTHONPATH=src` y luego `python -m ...`

---

## Paso 2 — Ejecutar las pruebas automatizadas

Son 72 pruebas que validan las estructuras de datos, los modelos, la
persistencia y la lógica de negocio.

```bash
# Todas las pruebas
PYTHONPATH=src python3 -m pytest

# Con el nombre de cada prueba (más detalle)
PYTHONPATH=src python3 -m pytest -v

# Rápido: omitir los benchmarks de rendimiento
PYTHONPATH=src python3 -m pytest -m "not benchmark"
```

**Resultado esperado:** `72 passed`.

Para ver los tiempos del benchmark (estructuras elegidas vs. alternativas
ingenuas, muestra la ventaja del heap y del AVL):

```bash
PYTHONPATH=src python3 -m pytest tests/test_benchmark.py -s
```

Probar un solo módulo, por ejemplo el árbol AVL:

```bash
PYTHONPATH=src python3 -m pytest tests/test_avl_tree.py -v
```

---

## Paso 3 — Ejecutar la demostración por consola

Carga los datos sintéticos de Colombia y muestra todo el flujo: lotes próximos a
caducar, alertas de desabastecimiento, asignación por triaje, balance de stock y
una ruta óptima.

```bash
PYTHONPATH=src python3 -m sistema_donaciones
```

Con un archivo de datos propio:

```bash
PYTHONPATH=src python3 -m sistema_donaciones --data mis_datos.json
```

---

## Paso 4 — Abrir la interfaz gráfica (GUI)

```bash
PYTHONPATH=src python3 -m sistema_donaciones --gui
```

Se abrirá la ventana **"UNGRD · Gestión y Distribución de Donaciones
Post-Desastre"** con cinco pestañas. Qué probar en cada una:

### Pestaña "Inventario"
- Muestra todos los lotes cargados (id, categoría, descripción, cantidad,
  caducidad y estado).
- El botón **Refrescar** vuelve a leer el estado actual.

### Pestaña "Registrar donación"
Formulario validado para ingresar un lote nuevo. Prueba estos casos:
1. **Caso válido:** completa ID (p. ej. `LOT-9001`), descripción, cantidad `100`,
   peso `50`, volumen `2`, fecha `2027-06-30`, elige categoría y donante →
   **Registrar**. Debe aparecer un mensaje de éxito y el lote en Inventario.
2. **Caso de error (validación):** pon una **cantidad negativa** (`-5`) o una
   **fecha anterior al evento** (`2025-01-01`). Debe salir un cuadro de error
   rojo explicando el problema, sin registrar nada. Esto demuestra la
   retroalimentación visual ante datos fuera de rango.

### Pestaña "Asignación / Triaje"
- Elige un **centro de origen** (p. ej. `CA-BOG`) y pulsa
  **Ejecutar asignación**.
- El sistema asigna los lotes a los municipios por orden de urgencia
  (los más críticos primero) y aplica FEFO (lo que caduca antes se despacha
  primero), mostrando además la ruta de despacho calculada con Dijkstra.
- La operación corre en un hilo aparte, por lo que la ventana **no se congela**.

### Pestaña "Alertas"
- Pulsa **Refrescar alertas** para ver el balance de stock por categoría,
  el total despachado vs. remanente y las alertas de desabastecimiento
  (categorías donde la demanda supera lo disponible).

### Pestaña "Rutas de despacho"
- Elige **Origen** y **Destino** (p. ej. `CA-BOG` → `MUN-001`) y pulsa
  **Calcular ruta óptima**. Muestra la secuencia de nodos y el costo total.

Para cerrar, simplemente cierra la ventana.

---

## Paso 5 (opcional) — Probar interactivamente en el intérprete

```bash
PYTHONPATH=src python3
```

```python
>>> from sistema_donaciones.structures import MinMaxHeap
>>> h = MinMaxHeap()
>>> for v in [5, 1, 9, 3]: h.push(v)
>>> h.peek_min(), h.peek_max()
(1, 9)

>>> from sistema_donaciones.core import construir_sistema
>>> s, carga = construir_sistema("data/datos_colombia.json")
>>> carga.resumen()
>>> s.alertas_desabastecimiento()
>>> s.ruta_optima("CA-BOG", "MUN-001")
```

---

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---------|-------|----------|
| `ModuleNotFoundError: No module named 'sistema_donaciones'` | Falta `PYTHONPATH=src` o no estás en la raíz del repo | Sitúate en la carpeta `SistemaDonaciones` y antepón `PYTHONPATH=src` |
| `ModuleNotFoundError: No module named 'tkinter'` | Tkinter no instalado (algunas distros de Linux) | `sudo apt install python3-tk` (Debian/Ubuntu) |
| La GUI no abre / `TclError: no display name` | Entorno sin pantalla (servidor/sandbox) | Ejecuta la GUI en un equipo con escritorio |
| `pytest: command not found` | pytest no instalado | `pip install pytest` |
