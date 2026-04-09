import re
from typing import Dict, List, Optional, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish


TITLE_TOKENS = [
    "ESTADO SEPARADO DE SITUACION FINANCIERA",
    "ESTADO CONSOLIDADO DE SITUACIÓN FINANCIERA",
    "ESTADO CONSOLIDADO DE SITUACION FINANCIERA",
]

LEFT_SECTIONS = {
    "ACTIVO",
    "Activo corriente",
    "Activo no corriente",
}

RIGHT_SECTIONS = {
    "PASIVO Y PATRIMONIO",
    "PASIVO Y PATRIMONIO NETO",
    "Pasivo corriente",
    "Pasivo no corriente",
    "PATRIMONIO",
}

LEFT_ROWS = [
    "Efectivo y equivalente de efectivo",
    "Cuentas por cobrar comerciales, neto",
    "Fondo de garantía para operaciones con derivados",
    "Otras cuentas por cobrar, neto",
    "Cuentas por cobrar a partes relacionadas",
    "Anticipos a proveedores",
    "Activo por impuesto a las ganancias",
    "Instrumentos financieros derivados",
    "Inventarios, neto",
    "Otros activos no financieros",
    "Activos clasificados como mantenidos para la venta, neto",
    "Total activo corriente",
    "Otros activos financieros",
    "Inversiones contabilizadas aplicando el método de participación",
    "Propiedades, planta y equipo, neto",
    "Activos intangibles, neto",
    "Activos por derecho de uso, neto",
    "Activo por impuesto a las ganancias diferido",
    "Plusvalía",
    "Plusvalía, neto",
    "Total activo no corriente",
    "TOTAL ACTIVO",
]

RIGHT_ROWS = [
    "Otros pasivos financieros",
    "Cuentas por pagar comerciales",
    "Otras cuentas por pagar",
    "Cuentas por pagar a partes relacionadas",
    "Beneficios a los empleados",
    "Instrumentos financieros derivados",
    "Pasivos por impuesto a las ganancias",
    "Provisiones",
    "Ingresos diferidos",
    "Total pasivo corriente",
    "Pasivo por impuesto a las ganancias diferido",
    "Total pasivo no corriente",
    "Total pasivo",
    "Capital emitido",
    "Acciones de inversión",
    "Acciones propias en cartera",
    "Otras reservas de capital",
    "Resultados acumulados",
    "Otras reservas de patrimonio",
    "Patrimonio atribuible a los propietarios de la controladora",
    "Participaciones no controladoras",
    "Total patrimonio",
    "TOTAL PASIVO Y PATRIMONIO",
]

ALL_ROWS = sorted(set(LEFT_ROWS + RIGHT_ROWS), key=len, reverse=True)
ALL_SECTIONS = sorted(LEFT_SECTIONS.union(RIGHT_SECTIONS), key=len, reverse=True)

YEAR_RE = re.compile(r"^20\d{2}$")
NOTE_RE = re.compile(r"^\d+\s*(?:\([A-Za-z,]+\))*$")


def _norm(s: str) -> str:
    return " ".join(s.split()).strip()


def _is_title_window(lines: List[str], i: int) -> bool:
    win = _norm(" ".join(lines[max(0, i - 12):i + 25]))
    low = win.lower()
    return any(t.lower() in low for t in TITLE_TOKENS)


def _extract_years(lines: List[str], i: int) -> Optional[Tuple[str, str]]:
    years: List[str] = []
    for ln in lines[i:i + 70]:
        token = _norm(ln)
        if YEAR_RE.match(token) and token not in years:
            years.append(token)
    if len(years) >= 2:
        return years[0], years[1]
    return None


def _looks_like_table_header_window(lines: List[str], i: int) -> bool:
    if not _is_title_window(lines, i):
        return False

    win = _norm(" ".join(lines[i:i + 70])).lower()
    if "nota" not in win:
        return False
    if "s/000" not in win:
        return False

    return _extract_years(lines, i) is not None


def _extract_unit(lines: List[str], i: int) -> str:
    for j in range(max(0, i - 10), min(len(lines), i + 15)):
        if "s/000" in lines[j].lower():
            return "S/000"
    return "unidad no identificada"


def _extract_table_title(lines: List[str], start_idx: int) -> str:
    candidates = []
    for j in range(max(0, start_idx - 12), start_idx + 8):
        ln = _norm(lines[j])
        if not ln:
            continue
        low = ln.lower()
        if low.startswith("por los años terminados") or low.startswith("al 31 de diciembre"):
            continue
        if low in {"nota", "s/000"}:
            continue
        if YEAR_RE.match(ln):
            continue
        candidates.append(ln)

    for c in candidates:
        if "ESTADO" in c.upper() and "SITUACION" in c.upper():
            return c
    return candidates[-1] if candidates else "Estado de situación financiera"


def _match_from(lines: List[str], i: int, labels: List[str], max_lines: int = 4) -> Optional[Tuple[str, int]]:
    parts: List[str] = []
    for span in range(1, max_lines + 1):
        if i + span - 1 >= len(lines):
            break
        piece = lines[i + span - 1].strip()
        if not piece:
            break
        parts.append(piece)
        cand = _norm(" ".join(parts))
        if cand in labels:
            return cand, i + span
    return None


def _consume_header(lines: List[str], start_idx: int) -> int:
    i = start_idx
    limit = min(len(lines), start_idx + 90)
    while i < limit:
        if _match_from(lines, i, ALL_SECTIONS, 3):
            return i
        if _match_from(lines, i, ALL_ROWS, 4):
            return i
        i += 1
    return i


def _looks_like_note(token: str) -> bool:
    t = _norm(token)
    if NOTE_RE.match(t):
        return True
    compact = t.replace(" ", "")
    return bool(re.match(r"^\d+(?:\([A-Za-z,]+\))*$", compact))


def _read_note_and_values(lines: List[str], i: int) -> Tuple[str, str, str, int]:
    note = "-"
    y_a = "-"
    y_b = "-"

    while i < len(lines) and not lines[i].strip():
        i += 1

    if i < len(lines):
        t = lines[i].strip()
        if _looks_like_note(t):
            note = _norm(t)
            i += 1

    vals: List[str] = []
    while i < len(lines) and len(vals) < 2:
        ln = lines[i].strip()

        if not ln:
            i += 1
            continue

        if _match_from(lines, i, ALL_SECTIONS, 3):
            break
        if _match_from(lines, i, ALL_ROWS, 4):
            break
        if "las notas que se acompañan" in ln.lower():
            break

        if not is_numericish(ln):
            break

        vals.append(ln)
        i += 1

    if len(vals) >= 1:
        y_a = vals[0]
    if len(vals) >= 2:
        y_b = vals[1]

    return note, y_a, y_b, i


def _infer_side(metric: str, section: str) -> str:
    if metric in LEFT_ROWS:
        return "activo"
    if metric in RIGHT_ROWS:
        return "pasivo_patrimonio"

    if section in LEFT_SECTIONS:
        return "activo"
    if section in RIGHT_SECTIONS:
        return "pasivo_patrimonio"
    return "desconocido"


def extract_financial_statements_tables_family_3(page_record: dict) -> List[Dict]:
    if (page_record.get("doc_type") or "").lower() != "financial_statements":
        return []

    text = (page_record.get("page_text") or "").strip()
    if not text:
        return []

    lines = normalize_lines(text)
    tables: List[Dict] = []
    i = 0

    while i < len(lines):
        if not _looks_like_table_header_window(lines, i):
            i += 1
            continue

        years = _extract_years(lines, i)
        if not years:
            i += 1
            continue
        year_a, year_b = years

        table_start = i
        unit = _extract_unit(lines, i)
        title = _extract_table_title(lines, i)
        cursor = _consume_header(lines, i)

        rows: List[Dict] = []
        current_section = ""

        while cursor < len(lines):
            ln = lines[cursor].strip()

            if not ln:
                cursor += 1
                continue

            if "las notas que se acompañan" in ln.lower():
                break

            sec_match = _match_from(lines, cursor, ALL_SECTIONS, 3)
            if sec_match:
                current_section, cursor = sec_match
                continue

            row_match = _match_from(lines, cursor, ALL_ROWS, 4)
            if not row_match:
                if len(ln.split()) >= 9 and not is_numericish(ln):
                    break
                cursor += 1
                continue

            metric, cursor = row_match
            note, v_a, v_b, cursor = _read_note_and_values(lines, cursor)

            rows.append(
                {
                    "side": _infer_side(metric, current_section),
                    "section": current_section,
                    "metric": metric,
                    "note": note,
                    "year_a": v_a,
                    "year_b": v_b,
                }
            )

        table_end = cursor
        if table_end > table_start and rows:
            page_record.setdefault("table_ranges", []).append((table_start, table_end))

        if rows:
            reconstructed_lines = [
                f"TABLA SITUACION FINANCIERA | Título: {title} | Unidad: {unit} | Años: {year_a}, {year_b}"
            ]
            for r in rows:
                reconstructed_lines.append(
                    f"[{r['side']}] {r['section']} | {r['metric']} | Nota: {r['note']} | {year_a}: {r['year_a']} | {year_b}: {r['year_b']}"
                )

            tables.append(
                {
                    "table_type": 9,
                    "title": title,
                    "unit": unit,
                    "years": [year_a, year_b],
                    "rows": rows,
                    "reconstructed_text": "\n".join(reconstructed_lines),
                }
            )

        i = cursor if cursor > i else i + 1

    return tables
