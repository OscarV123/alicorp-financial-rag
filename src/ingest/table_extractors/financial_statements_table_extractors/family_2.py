import re
from typing import Dict, List, Optional, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish


ISI_TITLE_TOKENS = [
    "ESTADO SEPARADO DE RESULTADOS INTEGRALES",
    "ESTADO CONSOLIDADO DE RESULTADOS INTEGRALES",
]

ISI_SECTION_ROWS = [
    "Otros resultados integrales",
    "Otros resultados integrales que se reclasificarán a resultados en periodos posteriores -",
    "Otros resultados integrales que no se reclasificarán a resultados en periodos posteriores -",
    "Impuesto a las ganancias relacionado con componentes de otros resultados integrales",
    "Atribuible a:",
]

ISI_ROW_LABELS = [
    "Utilidad neta",
    "Utilidad (Pérdida) neta",
    "Variación neta por coberturas del flujo de efectivo",
    "Variación neta por cobertura de una inversión neta en un negocio en el extranjero",
    "Variación neta por coberturas de una inversión neta de un negocio en el extranjero",
    "Diferencia de cambio por conversión de operaciones en el extranjero",
    "Participación en partidas patrimoniales de subsidiarias",
    "Otros movimientos",
    "Coberturas del flujo de efectivo",
    "Coberturas de traslación",
    "Cobertura de una inversión neta en un negocio en el extranjero",
    "Otros resultados integrales que se reclasificarán a resultados en periodos posteriores",
    "Otros resultados integrales que no se reclasificarán a resultados en periodos posteriores",
    "Impuesto a las ganancias relacionado con componentes de otros resultados integrales",
    "Otros resultados integrales netos del impuesto a las ganancias",
    "Total resultados integrales",
    "Propietarios de la controladora",
    "Participaciones no controladoras",
]

ISI_ROW_LABELS = sorted(ISI_ROW_LABELS, key=len, reverse=True)
ISI_SECTION_ROWS = sorted(ISI_SECTION_ROWS, key=len, reverse=True)

NOTE_RE = re.compile(r"^\d+\s*(?:\([A-Za-z]+\))*$")
YEAR_RE = re.compile(r"^(20\d{2})$")


def _norm(s: str) -> str:
    return " ".join(s.split()).strip()


def _looks_like_integral_title(lines: List[str], i: int) -> bool:
    window = _norm(" ".join(lines[max(0, i - 12):i + 12]))
    return any(t in window for t in ISI_TITLE_TOKENS)


def _extract_years_from_header(lines: List[str], i: int) -> Optional[Tuple[str, str]]:
    window_lines = lines[i:i + 60]
    years = []
    for ln in window_lines:
        token = _norm(ln)
        m = YEAR_RE.match(token)
        if m:
            y = m.group(1)
            if y not in years:
                years.append(y)
    if len(years) >= 2:
        return years[0], years[1]
    return None


def _looks_like_table_header_window(lines: List[str], i: int) -> bool:
    # Estricto: debe verse título integral + Nota + 2 años + S/000 cerca
    if not _looks_like_integral_title(lines, i):
        return False

    window = _norm(" ".join(lines[i:i + 60]))
    low = window.lower()

    if "nota" not in low:
        return False
    if "s/000" not in low:
        return False

    years = _extract_years_from_header(lines, i)
    return years is not None


def _extract_unit(lines: List[str], i: int) -> str:
    for j in range(max(0, i - 12), min(len(lines), i + 12)):
        if "s/000" in lines[j].lower():
            return "S/000"
    return "unidad no identificada"


def _extract_table_title(lines: List[str], start_idx: int) -> str:
    candidates = []
    for j in range(max(0, start_idx - 12), start_idx + 6):
        ln = _norm(lines[j])
        if not ln:
            continue
        low = ln.lower()

        if low.startswith("por el año terminado") or low.startswith("por los años terminados"):
            continue
        if low in {"nota", "s/000"}:
            continue
        if YEAR_RE.match(ln):
            continue
        if ln.startswith("(") and ln.endswith(")"):
            continue
        if not any(ch.isalpha() for ch in ln):
            continue

        candidates.append(ln)

    for c in candidates:
        if "RESULTADOS INTEGRALES" in c.upper():
            return c
    return candidates[-1] if candidates else "Estado de resultados integrales"


def _match_from(lines: List[str], i: int, labels: List[str], max_lines: int = 4) -> Optional[Tuple[str, int]]:
    parts: List[str] = []
    for span in range(1, max_lines + 1):
        if i + span - 1 >= len(lines):
            break
        piece = lines[i + span - 1].strip()
        if not piece:
            break
        parts.append(piece)
        candidate = _norm(" ".join(parts))
        if candidate in labels:
            return candidate, i + span
    return None


def _consume_header(lines: List[str], start_idx: int) -> int:
    i = start_idx
    limit = min(len(lines), start_idx + 90)
    while i < limit:
        if _match_from(lines, i, ISI_SECTION_ROWS, max_lines=3):
            return i
        if _match_from(lines, i, ISI_ROW_LABELS, max_lines=4):
            return i
        i += 1
    return i


def _is_note_token(token: str) -> bool:
    token = _norm(token)
    if NOTE_RE.match(token):
        return True
    return token.isdigit() and len(token) <= 3


def _read_note_and_values(lines: List[str], i: int) -> Tuple[str, str, str, int]:
    note = "-"
    y_a = "-"
    y_b = "-"

    while i < len(lines) and not lines[i].strip():
        i += 1

    if i < len(lines):
        maybe_note = lines[i].strip()
        if _is_note_token(maybe_note):
            note = _norm(maybe_note)
            i += 1

    vals: List[str] = []
    while i < len(lines) and len(vals) < 2:
        ln = lines[i].strip()

        if not ln:
            i += 1
            continue

        if _match_from(lines, i, ISI_SECTION_ROWS, max_lines=3):
            break
        if _match_from(lines, i, ISI_ROW_LABELS, max_lines=4):
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


def extract_financial_statements_tables_family_2(page_record: dict) -> List[Dict]:
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

        years = _extract_years_from_header(lines, i)
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

            sec_match = _match_from(lines, cursor, ISI_SECTION_ROWS, max_lines=3)
            if sec_match:
                current_section, cursor = sec_match
                continue

            metric_match = _match_from(lines, cursor, ISI_ROW_LABELS, max_lines=4)
            if not metric_match:
                if len(ln.split()) >= 9 and not is_numericish(ln):
                    break
                cursor += 1
                continue

            metric, cursor = metric_match
            note, v_a, v_b, cursor = _read_note_and_values(lines, cursor)

            rows.append(
                {
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
                f"TABLA RESULTADOS INTEGRALES | Título: {title} | Unidad: {unit} | Años: {year_a}, {year_b}"
            ]
            for r in rows:
                reconstructed_lines.append(
                    f"{r['section']} | {r['metric']} | Nota: {r['note']} | {year_a}: {r['year_a']} | {year_b}: {r['year_b']}"
                )

            tables.append(
                {
                    "table_type": 8,
                    "title": title,
                    "unit": unit,
                    "years": [year_a, year_b],
                    "rows": rows,
                    "reconstructed_text": "\n".join(reconstructed_lines),
                }
            )

        i = cursor if cursor > i else i + 1

    return tables
