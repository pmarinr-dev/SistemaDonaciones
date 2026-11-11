#!/usr/bin/env python3
"""Conversor Markdown -> PDF en Python puro (sin dependencias externas).

Pensado para generar el informe del proyecto cuando no hay pandoc, weasyprint
ni acceso a PyPI. Soporta un subconjunto de Markdown suficiente para el
informe:

    - Encabezados #, ##, ###
    - Párrafos con **negrita**, *cursiva* y `código en línea`
    - Listas con viñetas (-, *) y numeradas (1.)
    - Tablas GitHub-flavored (| col | col |)
    - Bloques de cita (>)
    - Reglas horizontales (---)
    - Bloques de código ```

Genera un PDF 1.4 válido escrito a mano: objetos, streams de contenido y
tabla xref. Usa las fuentes base de PDF (Helvetica / Helvetica-Bold /
Helvetica-Oblique / Courier) con codificación WinAnsi para acentos del
español. Las tablas y el código se renderizan en Courier (monoespaciado).

Uso:
    python3 tools/md_to_pdf.py docs/INFORME.md docs/INFORME.pdf
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import List, Tuple

# --------------------------------------------------------------------------- #
# Geometría de página (A4 en puntos, 72 pt = 1 pulgada)
# --------------------------------------------------------------------------- #
PAGE_W, PAGE_H = 595.0, 842.0
MARGIN_X = 56.0
MARGIN_TOP = 64.0
MARGIN_BOT = 56.0
CONTENT_W = PAGE_W - 2 * MARGIN_X

# Anchos de glifo aproximados para Helvetica (por 1000 unidades de em).
# Permite ajustar líneas con un ancho razonable sin incrustar métricas AFM.
_HELV_WIDTHS = {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667,
    "'": 191, "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333,
    ".": 278, "/": 278, "0": 556, "1": 556, "2": 556, "3": 556, "4": 556,
    "5": 556, "6": 556, "7": 556, "8": 556, "9": 556, ":": 278, ";": 278,
    "<": 584, "=": 584, ">": 584, "?": 556, "@": 1015, "[": 278, "\\": 278,
    "]": 278, "^": 469, "_": 556, "`": 333, "{": 334, "|": 260, "}": 334,
    "~": 584,
}
for _c in "abcdefghijklmnopqrstuvwxyz":
    _HELV_WIDTHS[_c] = {"i": 222, "j": 222, "l": 222, "f": 278, "t": 278,
                        "r": 333, "m": 833, "w": 722}.get(_c, 556)
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    _HELV_WIDTHS[_c] = {"I": 278, "J": 500, "M": 833, "W": 944}.get(_c, 667)


def _char_width(ch: str, size: float, mono: bool) -> float:
    if mono:
        return 600 / 1000 * size  # Courier es fijo a 600
    return _HELV_WIDTHS.get(ch, 556) / 1000 * size


def text_width(s: str, size: float, mono: bool = False) -> float:
    return sum(_char_width(c, size, mono) for c in s)


# --------------------------------------------------------------------------- #
# Codificación WinAnsi para acentos / símbolos del español e informe
# --------------------------------------------------------------------------- #
_WINANSI = {
    "á": 0xE1, "é": 0xE9, "í": 0xED, "ó": 0xF3, "ú": 0xFA, "ñ": 0xF1,
    "Á": 0xC1, "É": 0xC9, "Í": 0xCD, "Ó": 0xD3, "Ú": 0xDA, "Ñ": 0xD1,
    "ü": 0xFC, "Ü": 0xDC, "¿": 0xBF, "¡": 0xA1, "°": 0xB0, "º": 0xBA,
    "ª": 0xAA, "«": 0xAB, "»": 0xBB, "“": 0x93, "”": 0x94, "‘": 0x91,
    "’": 0x92, "–": 0x96, "—": 0x97, "…": 0x85, "•": 0x95, "€": 0x80,
    "·": 0xB7, "²": 0xB2, "³": 0xB3, "×": 0xD7,
}
# Caracteres sin glifo en WinAnsi: se transliteran a ASCII aproximado.
_TRANSLIT = {
    "→": "->", "←": "<-", "≈": "~", "≤": "<=", "≥": ">=", "⌊": "|", "⌋": "|",
    "√": "sqrt", "⚠": "!", "│": "|", "├": "|", "└": "|",
    "₂": "2", "₀": "0",
}


def _sanitize(s: str) -> str:
    out = []
    for ch in s:
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
        else:
            out.append(ch)
    return "".join(out)


def _pdf_escape(s: str) -> bytes:
    """Convierte texto a bytes WinAnsi escapados para un literal PDF."""
    s = _sanitize(s)
    buf = bytearray()
    for ch in s:
        code = _WINANSI.get(ch)
        if code is None:
            o = ord(ch)
            code = o if o < 128 else ord("?")
        if code in (0x28, 0x29, 0x5C):  # ( ) \
            buf.append(0x5C)
        buf.append(code)
    return bytes(buf)


# --------------------------------------------------------------------------- #
# Modelo de "runs" con estilo (negrita/cursiva/código)
# --------------------------------------------------------------------------- #
@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False


_INLINE_RE = re.compile(
    r"(\*\*.+?\*\*|__.+?__|\*.+?\*|_.+?_|`.+?`)", re.DOTALL
)


def parse_inline(text: str) -> List[Run]:
    runs: List[Run] = []
    for part in _INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            runs.append(Run(part[2:-2], bold=True))
        elif part.startswith("__") and part.endswith("__"):
            runs.append(Run(part[2:-2], bold=True))
        elif part.startswith("`") and part.endswith("`"):
            runs.append(Run(part[1:-1], code=True))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            runs.append(Run(part[1:-1], italic=True))
        elif part.startswith("_") and part.endswith("_") and len(part) > 2:
            runs.append(Run(part[1:-1], italic=True))
        else:
            runs.append(Run(part))
    return runs


def _font_for(run: Run) -> str:
    if run.code:
        return "F4"  # Courier
    if run.bold:
        return "F2"  # Helvetica-Bold
    if run.italic:
        return "F3"  # Helvetica-Oblique
    return "F1"      # Helvetica


# --------------------------------------------------------------------------- #
# Composición de líneas (word-wrap sobre runs)
# --------------------------------------------------------------------------- #
@dataclass
class Piece:
    text: str
    font: str
    size: float
    mono: bool


def wrap_runs(runs: List[Run], size: float, max_w: float) -> List[List[Piece]]:
    """Divide los runs en líneas que caben en `max_w`."""
    lines: List[List[Piece]] = []
    cur: List[Piece] = []
    cur_w = 0.0

    # Tokeniza en palabras conservando el estilo de cada una.
    tokens: List[Tuple[str, Run]] = []
    for run in runs:
        parts = re.split(r"(\s+)", run.text)
        for p in parts:
            if p != "":
                tokens.append((p, run))

    for tok, run in tokens:
        mono = run.code
        font = _font_for(run)
        w = text_width(tok, size, mono)
        is_space = tok.strip() == ""
        if cur_w + w > max_w and cur and not is_space:
            lines.append(cur)
            cur, cur_w = [], 0.0
        if is_space and not cur:
            continue  # no iniciar línea con espacio
        cur.append(Piece(tok, font, size, mono))
        cur_w += w
    if cur:
        lines.append(cur)
    return lines or [[Piece("", "F1", size, False)]]


# --------------------------------------------------------------------------- #
# Constructor de contenido de página
# --------------------------------------------------------------------------- #
class PdfBuilder:
    def __init__(self) -> None:
        self.pages: List[List[bytes]] = []
        self._ops: List[bytes] = []
        self.y = PAGE_H - MARGIN_TOP

    # -- gestión de páginas --------------------------------------------- #
    def _new_page(self) -> None:
        if self._ops:
            self.pages.append(self._ops)
        self._ops = []
        self.y = PAGE_H - MARGIN_TOP

    def finish(self) -> None:
        if self._ops:
            self.pages.append(self._ops)

    def _ensure(self, needed: float) -> None:
        if self.y - needed < MARGIN_BOT:
            self._new_page()

    # -- primitivas de dibujo ------------------------------------------- #
    def _draw_pieces(self, pieces: List[Piece], x: float, y: float,
                     color: Tuple[float, float, float] = (0, 0, 0)) -> None:
        r, g, b = color
        self._ops.append(b"BT")
        self._ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg".encode("latin-1"))
        cursor = x
        last_font = None
        last_size = None
        for pc in pieces:
            if pc.font != last_font or pc.size != last_size:
                self._ops.append(f"/{pc.font} {pc.size:.1f} Tf".encode("latin-1"))
                last_font, last_size = pc.font, pc.size
            self._ops.append(f"1 0 0 1 {cursor:.2f} {y:.2f} Tm".encode("latin-1"))
            self._ops.append(b"(" + _pdf_escape(pc.text) + b") Tj")
            cursor += text_width(pc.text, pc.size, pc.mono)
        self._ops.append(b"ET")

    def _fill_rect(self, x: float, y: float, w: float, h: float,
                   color: Tuple[float, float, float]) -> None:
        r, g, b = color
        self._ops.append(
            f"{r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f".encode("latin-1")
        )

    def _line(self, x1: float, y1: float, x2: float, y2: float,
              width: float = 0.6, color: Tuple[float, float, float] = (0.7, 0.7, 0.7)) -> None:
        r, g, b = color
        self._ops.append(
            f"{r:.3f} {g:.3f} {b:.3f} RG {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S".encode("latin-1")
        )

    # -- bloques de alto nivel ------------------------------------------ #
    def heading(self, level: int, text: str) -> None:
        sizes = {1: 20.0, 2: 15.0, 3: 12.5}
        size = sizes.get(level, 11.0)
        gap_before = {1: 10, 2: 18, 3: 12}.get(level, 8)
        self.y -= gap_before
        runs = [Run(text, bold=True)]
        lines = wrap_runs(runs, size, CONTENT_W)
        for ln in lines:
            self._ensure(size + 6)
            for pc in ln:
                pc.font = "F2"
            color = (0.09, 0.19, 0.36) if level <= 2 else (0.15, 0.15, 0.15)
            self._draw_pieces(ln, MARGIN_X, self.y - size, color)
            self.y -= size + 5
        if level == 1:
            self._ensure(8)
            self._line(MARGIN_X, self.y - 2, PAGE_W - MARGIN_X, self.y - 2,
                       width=1.0, color=(0.09, 0.19, 0.36))
            self.y -= 10
        else:
            self.y -= 3

    def paragraph(self, text: str, indent: float = 0.0, size: float = 10.0,
                  color: Tuple[float, float, float] = (0.1, 0.1, 0.1)) -> None:
        runs = parse_inline(text)
        lines = wrap_runs(runs, size, CONTENT_W - indent)
        leading = size * 1.42
        for ln in lines:
            self._ensure(leading)
            self._draw_pieces(ln, MARGIN_X + indent, self.y - size, color)
            self.y -= leading
        self.y -= 2

    def bullet(self, text: str, ordered_num: int | None = None) -> None:
        size = 10.0
        marker = f"{ordered_num}." if ordered_num is not None else "-"
        indent = 16.0
        runs = parse_inline(text)
        lines = wrap_runs(runs, size, CONTENT_W - indent)
        leading = size * 1.42
        first = True
        for ln in lines:
            self._ensure(leading)
            if first:
                self._draw_pieces([Piece(marker, "F2", size, False)],
                                  MARGIN_X, self.y - size, (0.09, 0.19, 0.36))
                first = False
            self._draw_pieces(ln, MARGIN_X + indent, self.y - size, (0.1, 0.1, 0.1))
            self.y -= leading
        self.y -= 1

    def quote(self, text: str) -> None:
        size = 9.5
        indent = 14.0
        runs = parse_inline(text)
        lines = wrap_runs(runs, size, CONTENT_W - indent - 6)
        leading = size * 1.42
        start_y = self.y
        block_pieces = []
        for ln in lines:
            self._ensure(leading)
            if self.y == start_y or True:
                pass
            self._draw_pieces(ln, MARGIN_X + indent, self.y - size, (0.3, 0.3, 0.3))
            # barra lateral de cita
            self._fill_rect(MARGIN_X + 2, self.y - size - 1, 2.5, leading,
                            (0.6, 0.6, 0.7))
            self.y -= leading
        self.y -= 3

    def code_block(self, lines: List[str]) -> None:
        size = 8.6
        leading = size * 1.35
        pad = 5.0
        block_h = leading * len(lines) + 2 * pad
        self._ensure(block_h)
        top = self.y
        self._fill_rect(MARGIN_X, top - block_h, CONTENT_W, block_h,
                        (0.95, 0.95, 0.96))
        y = top - pad - size
        for raw in lines:
            text = raw.replace("\t", "    ")
            # recorte si excede el ancho
            max_chars = int((CONTENT_W - 2 * pad) / (600 / 1000 * size))
            if len(text) > max_chars:
                text = text[:max_chars]
            self._draw_pieces([Piece(text, "F4", size, True)],
                              MARGIN_X + pad, y, (0.12, 0.12, 0.12))
            y -= leading
        self.y = top - block_h - 6

    def table(self, header: List[str], rows: List[List[str]]) -> None:
        size = 8.6
        pad = 4.0
        ncol = len(header)
        col_w = CONTENT_W / ncol
        line_h = size * 1.3

        def cell_lines(text: str) -> List[List[Piece]]:
            return wrap_runs(parse_inline(text), size, col_w - 2 * pad)

        def row_height(cells: List[str]) -> float:
            maxl = max((len(cell_lines(c)) for c in cells), default=1)
            return maxl * line_h + 2 * pad

        def draw_row(cells: List[str], header_row: bool) -> None:
            h = row_height(cells)
            self._ensure(h)
            top = self.y
            if header_row:
                self._fill_rect(MARGIN_X, top - h, CONTENT_W, h, (0.09, 0.19, 0.36))
            # bordes verticales y celdas
            for i, cell in enumerate(cells):
                cx = MARGIN_X + i * col_w
                clines = cell_lines(cell)
                ty = top - pad - size
                for ln in clines:
                    if header_row:
                        for pc in ln:
                            pc.font = "F2"
                        col = (1, 1, 1)
                    else:
                        col = (0.12, 0.12, 0.12)
                    self._draw_pieces(ln, cx + pad, ty, col)
                    ty -= line_h
            # línea inferior
            self._line(MARGIN_X, top - h, PAGE_W - MARGIN_X, top - h,
                       width=0.5, color=(0.8, 0.8, 0.8))
            self.y = top - h

        draw_row(header, True)
        for r in rows:
            # normaliza nº de columnas
            r = (r + [""] * ncol)[:ncol]
            draw_row(r, False)
        self.y -= 8

    def hrule(self) -> None:
        self._ensure(12)
        self._line(MARGIN_X, self.y - 4, PAGE_W - MARGIN_X, self.y - 4,
                   width=0.6, color=(0.75, 0.75, 0.75))
        self.y -= 12

    def spacer(self, h: float) -> None:
        self.y -= h

    def cover(self, title: str, subtitle: str,
              authors: List[str] | None = None) -> None:
        """Portada centrada en la primera página."""
        self.y = PAGE_H * 0.66
        size = 22.0
        for line in _center_wrap(title, size, CONTENT_W):
            w = text_width(line, size, False)
            self._draw_pieces([Piece(line, "F2", size, False)],
                              (PAGE_W - w) / 2, self.y, (0.09, 0.19, 0.36))
            self.y -= size * 1.3
        self.y -= 14
        ssize = 12.0
        for line in _center_wrap(subtitle, ssize, CONTENT_W):
            w = text_width(line, ssize, False)
            self._draw_pieces([Piece(line, "F3", ssize, False)],
                              (PAGE_W - w) / 2, self.y, (0.25, 0.25, 0.25))
            self.y -= ssize * 1.4
        # línea decorativa
        self.y -= 10
        self._line(PAGE_W * 0.3, self.y, PAGE_W * 0.7, self.y,
                   width=1.2, color=(0.09, 0.19, 0.36))
        self.y -= 28
        # Autores
        if authors:
            lbl = "Autores"
            w = text_width(lbl, 11.0, False)
            self._draw_pieces([Piece(lbl, "F2", 11.0, False)],
                              (PAGE_W - w) / 2, self.y, (0.09, 0.19, 0.36))
            self.y -= 20
            for name in authors:
                w = text_width(name, 11.5, False)
                self._draw_pieces([Piece(name, "F1", 11.5, False)],
                                  (PAGE_W - w) / 2, self.y, (0.15, 0.15, 0.15))
                self.y -= 17
        self._new_page()


def _center_wrap(text: str, size: float, max_w: float) -> List[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if text_width(trial, size, False) > max_w and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------------------- #
# Parser de Markdown -> llamadas al builder
# --------------------------------------------------------------------------- #
def _split_table_row(line: str) -> List[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _is_sep_row(line: str) -> bool:
    return bool(re.fullmatch(r"\s*\|?[\s:\-|]+\|?\s*", line)) and "-" in line


def render(md: str, builder: PdfBuilder) -> None:
    lines = md.splitlines()
    i = 0
    first_h1_done = False
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Bloque de código ```
        if stripped.startswith("```"):
            j = i + 1
            code: List[str] = []
            while j < n and not lines[j].strip().startswith("```"):
                code.append(lines[j])
                j += 1
            builder.code_block(code if code else [""])
            i = j + 1
            continue

        # Tabla
        if "|" in line and i + 1 < n and _is_sep_row(lines[i + 1]):
            header = _split_table_row(line)
            rows = []
            j = i + 2
            while j < n and "|" in lines[j] and lines[j].strip():
                rows.append(_split_table_row(lines[j]))
                j += 1
            builder.table(header, rows)
            i = j
            continue

        # Vacío
        if stripped == "":
            builder.spacer(3)
            i += 1
            continue

        # Regla horizontal
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            builder.hrule()
            i += 1
            continue

        # Encabezados
        m = re.match(r"(#{1,6})\s+(.*)", stripped)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            if level == 1 and not first_h1_done:
                # La primera H1 ya está en la portada: omitir aquí.
                first_h1_done = True
                i += 1
                continue
            builder.heading(level, text)
            i += 1
            continue

        # Cita
        if stripped.startswith(">"):
            quote_text = stripped[1:].strip()
            j = i + 1
            while j < n and lines[j].strip().startswith(">"):
                quote_text += " " + lines[j].strip()[1:].strip()
                j += 1
            builder.quote(quote_text)
            i = j
            continue

        # Lista numerada
        m = re.match(r"(\d+)\.\s+(.*)", stripped)
        if m:
            num = int(m.group(1))
            text = m.group(2)
            j = i + 1
            while j < n and lines[j].startswith("   ") and lines[j].strip():
                text += " " + lines[j].strip()
                j += 1
            builder.bullet(text, ordered_num=num)
            i = j
            continue

        # Viñeta
        m = re.match(r"[-*]\s+(.*)", stripped)
        if m:
            text = m.group(1)
            j = i + 1
            while j < n and lines[j].startswith("  ") and lines[j].strip() and \
                    not re.match(r"\s*[-*]\s+", lines[j]):
                text += " " + lines[j].strip()
                j += 1
            builder.bullet(text)
            i = j
            continue

        # Párrafo (une líneas contiguas)
        para = stripped
        j = i + 1
        while j < n and lines[j].strip() and not _para_breaks(lines[j]):
            para += " " + lines[j].strip()
            j += 1
        builder.paragraph(para)
        i = j


def _para_breaks(line: str) -> bool:
    s = line.strip()
    return (
        s.startswith("#")
        or s.startswith(">")
        or s.startswith("```")
        or s.startswith("- ")
        or s.startswith("* ")
        or bool(re.match(r"\d+\.\s", s))
        or ("|" in s)
        or bool(re.fullmatch(r"-{3,}|\*{3,}|_{3,}", s))
    )


# --------------------------------------------------------------------------- #
# Serialización del archivo PDF
# --------------------------------------------------------------------------- #
def build_pdf(pages_ops: List[List[bytes]], title: str) -> bytes:
    objects: List[bytes] = []

    def add_obj(body: bytes) -> int:
        objects.append(body)
        return len(objects)  # número de objeto (1-based)

    # Fuentes base
    font_objs = {}
    for fid, base in [("F1", "Helvetica"), ("F2", "Helvetica-Bold"),
                      ("F3", "Helvetica-Oblique"), ("F4", "Courier")]:
        num = add_obj(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /" + base.encode()
            + b" /Encoding /WinAnsiEncoding >>"
        )
        font_objs[fid] = num

    font_dict = b"<< " + b" ".join(
        f"/{fid} {num} 0 R".encode() for fid, num in font_objs.items()
    ) + b" >>"
    resources_num = add_obj(b"<< /Font " + font_dict + b" >>")

    # Reservamos el número del catálogo y del árbol de páginas.
    # Creamos primero los content streams y páginas.
    page_nums: List[int] = []
    content_nums: List[int] = []

    # El objeto Pages tendrá un número que aún no conocemos; usamos un
    # marcador y lo resolvemos al final asignándolo explícitamente.
    pages_obj_num = None  # se asigna después

    # Para enlazar /Parent necesitamos el número de Pages de antemano.
    # Estrategia: reservar el siguiente número disponible para Pages.
    pages_obj_num = len(objects) + 1 + 2 * len(pages_ops) + 0  # estimación
    # Más robusto: construir en orden conocido.
    objects_fixed: List[Tuple[int, bytes]] = [(i + 1, o) for i, o in enumerate(objects)]

    base = len(objects)  # objetos ya creados (fuentes + resources)
    # Asignación determinista de números:
    #   content_i  = base + 1 + 2*i
    #   page_i     = base + 2 + 2*i
    #   pages      = base + 1 + 2*N
    #   catalog    = base + 2 + 2*N
    N = len(pages_ops)
    for idx in range(N):
        content_nums.append(base + 1 + 2 * idx)
        page_nums.append(base + 2 + 2 * idx)
    pages_num = base + 1 + 2 * N
    catalog_num = base + 2 + 2 * N

    # Crea realmente los objetos de contenido y página en ese orden.
    for idx, ops in enumerate(pages_ops):
        stream = b"\n".join(ops)
        content = (
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
            + stream + b"\nendstream"
        )
        add_obj(content)  # ocupa content_nums[idx]
        page = (
            b"<< /Type /Page /Parent " + str(pages_num).encode()
            + b" 0 R /MediaBox [0 0 " + f"{PAGE_W:.0f} {PAGE_H:.0f}".encode()
            + b"] /Resources " + str(resources_num).encode()
            + b" 0 R /Contents " + str(content_nums[idx]).encode() + b" 0 R >>"
        )
        add_obj(page)  # ocupa page_nums[idx]

    kids = b" ".join(f"{pn} 0 R".encode() for pn in page_nums)
    add_obj(
        b"<< /Type /Pages /Kids [" + kids + b"] /Count "
        + str(N).encode() + b" >>"
    )  # pages_num
    add_obj(
        b"<< /Type /Catalog /Pages " + str(pages_num).encode() + b" 0 R >>"
    )  # catalog_num

    # Ensamblar el archivo con tabla xref.
    out = bytearray()
    out += b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"

    xref_pos = len(out)
    count = len(objects) + 1
    out += b"xref\n0 " + str(count).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        b"trailer\n<< /Size " + str(count).encode()
        + b" /Root " + str(catalog_num).encode() + b" 0 R >>\n"
        + b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF"
    )
    return bytes(out)


def _extract_authors(md: str) -> List[str]:
    """Extrae los nombres del bloque '**Autores:**' si existe."""
    m = re.search(r"\*\*Autores:\*\*\s*\n(.*?)(?:\n\s*\n|\n---)", md, re.S)
    if not m:
        return []
    return [
        re.sub(r"^[-*]\s+", "", ln).strip()
        for ln in m.group(1).splitlines()
        if ln.strip().startswith(("-", "*"))
    ]


def convert(md_path: str, pdf_path: str) -> None:
    with open(md_path, "r", encoding="utf-8") as fh:
        md = fh.read()

    authors = _extract_authors(md)

    builder = PdfBuilder()
    builder.cover(
        "Informe Técnico — Sistema de Gestión y Distribución de Donaciones Post-Desastre",
        "Universidad EAFIT · Estructuras de Datos y Algoritmos · Evaluación Práctica 3",
        authors=authors,
    )
    render(md, builder)
    builder.finish()

    pdf_bytes = build_pdf(builder.pages, title="Informe Técnico")
    with open(pdf_path, "wb") as fh:
        fh.write(pdf_bytes)
    print(f"PDF generado: {pdf_path} ({len(pdf_bytes)} bytes, {len(builder.pages)} páginas)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 tools/md_to_pdf.py ENTRADA.md SALIDA.pdf")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
