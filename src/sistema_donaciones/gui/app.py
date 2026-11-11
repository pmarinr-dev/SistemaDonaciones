"""Panel de control Tkinter para operadores de emergencia (Fase 4).

Diseño orientado a crisis: paneles diferenciados por pestañas, tablas
dinámicas de inventario, formulario validado de ingreso de ayuda, consola
de alertas de prioridad y cálculo de rutas de despacho.

Para evitar congelamiento de la UI, las operaciones potencialmente lentas
(asignación, Dijkstra sobre toda la red) se ejecutan en un hilo de trabajo
y el resultado se vuelca a los widgets mediante `root.after`, el mecanismo
seguro de Tkinter para actualizaciones desde fuera del hilo principal.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import messagebox, ttk

from ..core import construir_sistema
from ..core.system import SistemaDonaciones
from ..models import CategoriaAyuda, Donante, EstadoLote, LoteAyuda
from ..models.entities import EVENTO_FECHA

_DEFAULT_DATA = Path(__file__).resolve().parents[3] / "data" / "datos_colombia.json"


class DashboardApp:
    """Ventana principal del sistema."""

    def __init__(self, root: tk.Tk, data_path: Optional[Path] = None) -> None:
        self.root = root
        self.root.title("UNGRD · Gestión y Distribución de Donaciones Post-Desastre")
        self.root.geometry("1024x680")

        data_path = data_path or _DEFAULT_DATA
        self.sistema, carga = construir_sistema(data_path)
        self._carga_errores = carga.errores

        self._build_style()
        self._build_header()
        self._build_tabs()
        self._refrescar_todo()

        if carga.errores:
            self._log_alerta(
                f"Carga completada con {len(carga.errores)} advertencia(s)."
            )

    # ------------------------------------------------------------------ #
    # Construcción de la UI
    # ------------------------------------------------------------------ #
    def _build_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Crit.TLabel", foreground="#b00020", font=("Segoe UI", 10, "bold"))

    def _build_header(self) -> None:
        bar = ttk.Frame(self.root, padding=8)
        bar.pack(fill="x")
        ttk.Label(
            bar,
            text="Panel de Control de Emergencia",
            style="Header.TLabel",
        ).pack(side="left")
        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(bar, textvariable=self.status_var).pack(side="right")

    def _build_tabs(self) -> None:
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)
        self._tab_inventario()
        self._tab_ingreso()
        self._tab_asignacion()
        self._tab_alertas()
        self._tab_rutas()

    # -- Pestaña Inventario ---------------------------------------------- #
    def _tab_inventario(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Inventario")

        cols = ("id", "categoria", "descripcion", "cantidad", "caducidad", "estado")
        self.tree_inv = ttk.Treeview(frame, columns=cols, show="headings", height=18)
        for c, w in zip(cols, (90, 90, 260, 80, 100, 100)):
            self.tree_inv.heading(c, text=c.capitalize())
            self.tree_inv.column(c, width=w, anchor="w")
        self.tree_inv.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree_inv.yview)
        sb.pack(side="right", fill="y")
        self.tree_inv.configure(yscrollcommand=sb.set)

        btns = ttk.Frame(self.root)
        ttk.Button(frame, text="Refrescar", command=self._refrescar_inventario).pack()

    def _refrescar_inventario(self) -> None:
        for item in self.tree_inv.get_children():
            self.tree_inv.delete(item)
        for lote in sorted(self.sistema.lotes.values(), key=lambda l: l.id):
            self.tree_inv.insert(
                "",
                "end",
                values=(
                    lote.id,
                    lote.categoria.value,
                    lote.descripcion,
                    lote.cantidad,
                    lote.fecha_caducidad.isoformat(),
                    lote.estado.value,
                ),
            )

    # -- Pestaña Ingreso de ayuda ---------------------------------------- #
    def _tab_ingreso(self) -> None:
        frame = ttk.Frame(self.nb, padding=16)
        self.nb.add(frame, text="Registrar donación")

        self.entries: dict[str, tk.Variable] = {}
        campos = [
            ("ID lote", "id", tk.StringVar()),
            ("Descripción", "descripcion", tk.StringVar()),
            ("Cantidad", "cantidad", tk.StringVar()),
            ("Peso (kg)", "peso_kg", tk.StringVar()),
            ("Volumen (m³)", "volumen_m3", tk.StringVar()),
            ("Fecha caducidad (YYYY-MM-DD)", "fecha_caducidad", tk.StringVar()),
        ]
        for i, (label, key, var) in enumerate(campos):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=4)
            ttk.Entry(frame, textvariable=var, width=36).grid(row=i, column=1, pady=4)
            self.entries[key] = var

        ttk.Label(frame, text="Categoría").grid(row=0, column=2, sticky="w", padx=12)
        self.cat_var = tk.StringVar(value=CategoriaAyuda.MEDICO.value)
        ttk.Combobox(
            frame,
            textvariable=self.cat_var,
            values=[c.value for c in CategoriaAyuda],
            state="readonly",
            width=18,
        ).grid(row=1, column=2, padx=12)

        ttk.Label(frame, text="Donante").grid(row=2, column=2, sticky="w", padx=12)
        self.don_var = tk.StringVar()
        self.cb_don = ttk.Combobox(
            frame, textvariable=self.don_var, state="readonly", width=18
        )
        self.cb_don.grid(row=3, column=2, padx=12)

        self.frio_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Requiere cadena de frío", variable=self.frio_var
        ).grid(row=4, column=2, sticky="w", padx=12)

        ttk.Button(frame, text="Registrar", command=self._registrar).grid(
            row=len(campos), column=1, pady=12, sticky="e"
        )

    def _registrar(self) -> None:
        """Valida el formulario y registra el lote, con feedback visual."""
        try:
            lote = LoteAyuda(
                id=self.entries["id"].get().strip(),
                categoria=self.cat_var.get(),
                descripcion=self.entries["descripcion"].get().strip(),
                cantidad=int(self.entries["cantidad"].get()),
                peso_kg=float(self.entries["peso_kg"].get()),
                volumen_m3=float(self.entries["volumen_m3"].get()),
                requiere_frio=self.frio_var.get(),
                fecha_caducidad=self.entries["fecha_caducidad"].get().strip(),
                donante_id=self.don_var.get().strip(),
            )
            self.sistema.registrar_donacion(lote)
        except ValueError as exc:
            messagebox.showerror("Dato inválido", str(exc))
            return
        messagebox.showinfo("Registrado", f"Lote {lote.id} registrado correctamente.")
        self._refrescar_inventario()
        self._refrescar_alertas()

    # -- Pestaña Asignación ---------------------------------------------- #
    def _tab_asignacion(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Asignación / Triaje")

        top = ttk.Frame(frame)
        top.pack(fill="x")
        ttk.Label(top, text="Centro de origen:").pack(side="left")
        self.origen_var = tk.StringVar()
        self.cb_origen = ttk.Combobox(
            top, textvariable=self.origen_var, state="readonly", width=12
        )
        self.cb_origen.pack(side="left", padx=6)
        ttk.Button(top, text="Ejecutar asignación", command=self._asignar).pack(
            side="left", padx=6
        )

        self.txt_asig = tk.Text(frame, height=22, wrap="none")
        self.txt_asig.pack(fill="both", expand=True, pady=6)

    def _asignar(self) -> None:
        """Lanza la asignación en un hilo para no congelar la UI."""
        self.status_var.set("Asignando recursos…")
        origen = self.origen_var.get() or None

        def trabajo() -> None:
            resultados = self.sistema.asignar_recursos(centro_origen=origen)
            self.root.after(0, lambda: self._mostrar_asignacion(resultados))

        threading.Thread(target=trabajo, daemon=True).start()

    def _mostrar_asignacion(self, resultados) -> None:
        self.txt_asig.delete("1.0", "end")
        if not resultados:
            self.txt_asig.insert("end", "No hubo asignaciones (sin stock o sin demanda).\n")
        for r in resultados:
            self.txt_asig.insert("end", str(r) + "\n")
        self.status_var.set(f"Asignación completa: {len(resultados)} despachos")
        self._refrescar_inventario()
        self._refrescar_alertas()

    # -- Pestaña Alertas ------------------------------------------------- #
    def _tab_alertas(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Alertas")
        ttk.Button(frame, text="Refrescar alertas", command=self._refrescar_alertas).pack(
            anchor="w"
        )
        self.txt_alertas = tk.Text(frame, height=24, wrap="word")
        self.txt_alertas.pack(fill="both", expand=True, pady=6)

    def _refrescar_alertas(self) -> None:
        self.txt_alertas.delete("1.0", "end")
        balance = self.sistema.balance_stock()
        self.txt_alertas.insert("end", "=== BALANCE DE STOCK (unidades) ===\n")
        for cat, fila in sorted(balance.items()):
            self.txt_alertas.insert("end", f"  {cat:10s}: {fila}\n")

        dvr = self.sistema.despachados_vs_remanentes()
        self.txt_alertas.insert(
            "end",
            f"\nDespachados: {dvr['despachados']}  |  Remanentes: {dvr['remanentes']}\n",
        )

        self.txt_alertas.insert("end", "\n=== ALERTAS DE DESABASTECIMIENTO ===\n")
        alertas = self.sistema.alertas_desabastecimiento()
        if not alertas:
            self.txt_alertas.insert("end", "  Sin déficits detectados.\n")
        for a in alertas:
            self.txt_alertas.insert(
                "end",
                f"  ⚠ {a['categoria']}: demanda {a['demanda']} / "
                f"disponible {a['disponible']} → déficit {a['deficit']}\n",
            )

    def _log_alerta(self, texto: str) -> None:
        if hasattr(self, "txt_alertas"):
            self.txt_alertas.insert("end", f"\n[info] {texto}\n")

    # -- Pestaña Rutas --------------------------------------------------- #
    def _tab_rutas(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Rutas de despacho")

        top = ttk.Frame(frame)
        top.pack(fill="x")
        ttk.Label(top, text="Origen:").pack(side="left")
        self.ruta_o = tk.StringVar()
        self.cb_ruta_o = ttk.Combobox(top, textvariable=self.ruta_o, state="readonly", width=12)
        self.cb_ruta_o.pack(side="left", padx=6)
        ttk.Label(top, text="Destino:").pack(side="left")
        self.ruta_d = tk.StringVar()
        self.cb_ruta_d = ttk.Combobox(top, textvariable=self.ruta_d, state="readonly", width=12)
        self.cb_ruta_d.pack(side="left", padx=6)
        ttk.Button(top, text="Calcular ruta óptima", command=self._calcular_ruta).pack(
            side="left", padx=6
        )

        self.txt_ruta = tk.Text(frame, height=20, wrap="word")
        self.txt_ruta.pack(fill="both", expand=True, pady=6)

    def _calcular_ruta(self) -> None:
        origen, destino = self.ruta_o.get(), self.ruta_d.get()
        if not origen or not destino:
            messagebox.showwarning("Faltan datos", "Seleccione origen y destino.")
            return
        ruta, costo = self.sistema.ruta_optima(origen, destino)
        self.txt_ruta.delete("1.0", "end")
        if not ruta:
            self.txt_ruta.insert("end", f"No existe ruta entre {origen} y {destino}.\n")
        else:
            self.txt_ruta.insert(
                "end",
                f"Ruta óptima {origen} → {destino}:\n  {' → '.join(ruta)}\n"
                f"  Costo total: {costo:.1f}\n",
            )

    # ------------------------------------------------------------------ #
    # Refresco global
    # ------------------------------------------------------------------ #
    def _refrescar_todo(self) -> None:
        donantes = sorted(self.sistema.donantes.keys())
        self.cb_don["values"] = donantes
        if donantes:
            self.don_var.set(donantes[0])

        nodos = sorted(self.sistema.red.vertices())
        centros = sorted(self.sistema.centros.keys())
        self.cb_origen["values"] = centros
        if centros:
            self.origen_var.set(centros[0])
        self.cb_ruta_o["values"] = nodos
        self.cb_ruta_d["values"] = nodos
        if len(nodos) >= 2:
            self.ruta_o.set(nodos[0])
            self.ruta_d.set(nodos[-1])

        self._refrescar_inventario()
        self._refrescar_alertas()


def main() -> None:
    root = tk.Tk()
    DashboardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
