"""Punto de entrada por consola.

Uso:
    python -m sistema_donaciones            # demo por consola
    python -m sistema_donaciones --gui      # lanza la interfaz Tkinter
    python -m sistema_donaciones --data ruta.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .core import construir_sistema

_DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data" / "datos_colombia.json"


def _demo_consola(data_path: Path) -> None:
    sistema, carga = construir_sistema(data_path)
    print("=" * 70)
    print("SISTEMA DE GESTIÓN Y DISTRIBUCIÓN DE DONACIONES POST-DESASTRE")
    print("=" * 70)
    print(f"Carga: {carga.resumen()}")
    if carga.errores:
        print("Advertencias de carga:")
        for e in carga.errores:
            print(f"  - {e}")

    print("\n--- Lotes próximos a caducar (90 días) ---")
    for lote in sistema.buscar_proximos_a_caducar(90):
        print(f"  {lote.id} {lote.categoria.value} caduca {lote.fecha_caducidad}")

    print("\n--- Alertas de desabastecimiento ---")
    for a in sistema.alertas_desabastecimiento():
        print(f"  {a['categoria']}: déficit {a['deficit']}")

    print("\n--- Asignación automatizada por triaje (origen CA-BOG) ---")
    for r in sistema.asignar_recursos(centro_origen="CA-BOG"):
        print(f"  {r}")

    print("\n--- Balance de stock tras asignación ---")
    for cat, fila in sorted(sistema.balance_stock().items()):
        print(f"  {cat:10s}: {fila}")

    print("\n--- Ruta óptima CA-BOG -> MUN-001 ---")
    ruta, costo = sistema.ruta_optima("CA-BOG", "MUN-001")
    print(f"  {' -> '.join(ruta)} (costo {costo:.1f})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sistema de donaciones post-desastre")
    parser.add_argument("--gui", action="store_true", help="lanzar interfaz gráfica")
    parser.add_argument("--data", type=Path, default=_DEFAULT_DATA, help="ruta JSON de datos")
    args = parser.parse_args()

    if args.gui:
        from .gui.app import main as gui_main

        gui_main()
    else:
        _demo_consola(args.data)


if __name__ == "__main__":
    main()
