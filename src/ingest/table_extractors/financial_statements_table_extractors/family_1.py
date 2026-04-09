import re
from typing import Dict, List, Optional, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish


RESULTS_TITLE_TOKENS = [
    "ESTADO SEPARADO DE RESULTADOS",
    "ESTADO CONSOLIDADO DE RESULTADOS",
]

RESULTS_EXCLUDE_TITLE_TOKENS = [
    "RESULTADOS INTEGRALES",
]

RESULTS_BODY_SIGNALS = [
    "Ventas a terceros",
    "Costo de ventas",
    "Utilidad bruta",
]

RESULTS_SECTION_ROWS = [
    "Operaciones continuas:",
    "Operaciones discontinuadas",
    "Atribuible a:",
    "Utilidad (Pérdida) neta por acción",
    "Utilidad neta por acción",
]

RESULTS_ROW_LABELS = [
    "Ventas a terceros",
    "Ventas a partes relacionadas",
    "Costo de ventas",
    "Utilidad bruta",
    "Gastos de ventas y distribución",
    "Gastos administrativos",
    "Resultado de operaciones con derivados de materias primas",
    "Otros ingresos y gastos, neto",
    "Otros ingresos",
    "Otros gastos",
    "Utilidad de operación",
    "Ingresos financieros",
    "Gastos financieros",
    "Diferencia de cambio, neta",
    "Diferencia de cambio neta",
    "Participación de los resultados netos y pérdida de la venta de subsidiarias y asociada",
    "Participación en los resultados netos de las asociadas",
    "Utilidad (Pérdida) antes del impuesto a las ganancias por operaciones continuas",
    "Utilidad antes del impuesto a las ganancias por operaciones continuas",
    "Impuesto a las ganancias",
    "Utilidad (Pérdida) neta por operaciones continuas",
    "Utilidad neta por operaciones continuas",
    "Pérdida después de impuestos a las ganancias por operaciones discontinuadas",
    "Utilidad (Pérdida) neta",
    "Utilidad neta",
    "Propietarios de la controladora",
    "Participaciones no controladoras",
    "Utilidad (Pérdida) básica y diluida por acción común y de inversión (S/)",
    "Utilidad básica y diluida por acción común y de inversión de operaciones continuas (S/)",
    "Utilidad básica y diluida por acción común y de inversión (S/)",
]

RESULTS_ROW_LABELS = sorted(RESULTS_ROW_LABELS, key=len, reverse=True)
YEAR_RE = re.compile(r"^20\d{2}$")
NOTE_RE = re.compile(r"^\d+\s*(?:\([A-Za-z]+\))*$")


def _norm(s: str) -> str:
    return " ".join(s.split()).strip()


def _extract_years(lines: List[str], i: int) -> Optional[Tuple[str, str]]:
    years: List[str] = []
    for ln in lines[i:i + 60]:
        token = _norm(ln)
        if YEAR_RE.match(token) and token not in years:
            years.append(token)
    if len(years) >= 2:
        return years[0], years[1]
    return None


def _looks_like_table_header_window(lines: List[str], i: int) -> bool:
    window_raw = _norm(" ".join(lines[i:i + 55]))
    window_low = window_raw.lower()

    if any(t.lower() in window_low for t in RESULTS_EXCLUDE_TITLE_TOKENS):
        return False

    if not any(t in window_raw for t in RESULTS_TITLE_TOKENS):
        return False

    if "nota" not in window_low or "s/000" not in window_low:
        return False

    years = _extract_years(lines, i)
    if not years:
        return False

    body_window = _norm(" ".join(lines[i:i + 130]))
    body_hits = sum(1 for s in RESULTS_BODY_SIGNALS if s in body_window)
    return body_hits >= 2


def _extract_unit(lines: List[str], i: int) -> str:
    for j in range(max(0, i - 8), min(len(lines), i + 12)):
        if "s/000" in lines[j].lower():
            return "S/000"
    return "unidad no identificada"


def _extract_table_title(lines: List[str], start_idx: int) -> str:
    candidates = []
    for j in range(max(0, start_idx - 10), start_idx + 3):
        ln = _norm(lines[j])
        if not ln:
            continue
        low = ln.lower()

        if low.startswith("por los años terminados") or low.startswith("por el año terminado"):
            continue
        if low in {"nota", "s/000", "(reexpresado)"}:
            continue
        if YEAR_RE.match(ln):
            continue
        if any(t.lower() in low for t in RESULTS_EXCLUDE_TITLE_TOKENS):
            continue
        candidates.append(ln)

    for c in candidates:
        if "ESTADO" in c.upper() and "RESULTADOS" in c.upper():
            return c
    return candidates[-1] if candidates else "Estado de resultados"


def _match_metric_at(lines: List[str], i: int, max_lines: int = 4) -> Optional[Tuple[str, int]]:
    parts: List[str] = []
    for span in range(1, max_lines + 1):
        if i + span - 1 >= len(lines):
            break
        piece = lines[i + span - 1].strip()
        if not piece:
            break
        parts.append(piece)
        candidate = _norm(" ".join(parts))
        if candidate in RESULTS_ROW_LABELS:
            return candidate, i + span
        if candidate in RESULTS_SECTION_ROWS:
            return candidate, i + span
    return None


def _consume_header(lines: List[str], start_idx: int) -> int:
    i = start_idx
    limit = min(len(lines), start_idx + 80)
    while i < limit:
        if _match_metric_at(lines, i):
            return i
        i += 1
    return i


def _looks_like_note(token: str) -> bool:
    token = _norm(token)
    if NOTE_RE.match(token):
        return True
    compact = token.replace(" ", "")
    return bool(re.match(r"^\d+(?:\([A-Za-z]+\))*$", compact))


def _read_note_and_values(lines: List[str], i: int) -> Tuple[str, str, str, int]:
    note = "-"
    val_a = "-"
    val_b = "-"

    while i < len(lines) and not lines[i].strip():
        i += 1

    if i < len(lines):
        token = lines[i].strip()
        if _looks_like_note(token):
            note = _norm(token)
            i += 1

    values: List[str] = []
    while i < len(lines) and len(values) < 2:
        ln = lines[i].strip()

        if not ln:
            i += 1
            continue

        if _looks_like_table_header_window(lines, i):
            break
        if _match_metric_at(lines, i):
            break
        if "las notas que se acompañan" in ln.lower():
            break
        if not is_numericish(ln):
            break

        values.append(ln)
        i += 1

    if len(values) >= 1:
        val_a = values[0]
    if len(values) >= 2:
        val_b = values[1]

    return note, val_a, val_b, i


def extract_financial_statements_tables_family_1(page_record: dict) -> List[Dict]:
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

            if _looks_like_table_header_window(lines, cursor):
                break

            if "las notas que se acompañan" in ln.lower():
                break

            metric_match = _match_metric_at(lines, cursor)
            if not metric_match:
                if len(ln.split()) >= 8 and not is_numericish(ln):
                    break
                cursor += 1
                continue

            metric, cursor = metric_match

            if metric in RESULTS_SECTION_ROWS:
                current_section = metric
                continue

            note, val_a, val_b, cursor = _read_note_and_values(lines, cursor)
            rows.append(
                {
                    "section": current_section,
                    "metric": metric,
                    "note": note,
                    "year_a": val_a,
                    "year_b": val_b,
                }
            )

        table_end = cursor
        if table_end > table_start and rows:
            page_record.setdefault("table_ranges", []).append((table_start, table_end))

        if rows:
            reconstructed_lines = [
                f"TABLA ESTADO DE RESULTADOS | Título: {title} | Unidad: {unit} | Años: {year_a}, {year_b}"
            ]
            for r in rows:
                reconstructed_lines.append(
                    f"{r['section']} | {r['metric']} | Nota: {r['note']} | {year_a}: {r['year_a']} | {year_b}: {r['year_b']}"
                )

            tables.append(
                {
                    "table_type": 7,
                    "title": title,
                    "unit": unit,
                    "years": [year_a, year_b],
                    "rows": rows,
                    "reconstructed_text": "\n".join(reconstructed_lines),
                }
            )

        i = cursor if cursor > i else i + 1

    return tables
