import re
import unicodedata
from typing import Dict, List, Optional, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish


TITLE_TOKENS = [
    "estado separado de cambios en el patrimonio neto",
    "estado consolidado de cambios en el patrimonio neto",
]

BODY_SIGNALS = [
    "saldos al 1 de enero",
    "resultado integral del ejercicio",
    "saldos al 31 de diciembre",
]

ROW_LABELS = [
    "Saldos al 1 de enero de 2021",
    "Saldos al 1 de enero de 2022",
    "Saldos al 31 de diciembre de 2021",
    "Saldos al 31 de diciembre de 2022",
    "Saldos al 31 de diciembre de 2023",
    "Utilidad neta",
    "Pérdida neta",
    "Otros resultados integrales, neto del impuesto a las ganancias",
    "Resultado integral del ejercicio",
    "Distribución de dividendos, nota 34(e)",
    "Distribución de dividendos, nota 34(f)",
    "Transacciones con pagos basados en acciones, nota 34(e)",
    "Transacciones con pagos basados en acciones, nota 34(f)",
    "Transacciones con acciones propias en cartera, nota 34(c)",
    "Transacciones con acciones propias en cartera, nota 36(c)",
    "Otros movimientos",
]

ROW_LABELS = sorted(ROW_LABELS, key=len, reverse=True)
YEAR_RE = re.compile(r"^20\d{2}$")


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _norm(s: str) -> str:
    s = " ".join(s.split()).strip()
    s = _strip_accents(s).lower()
    return s


def _looks_like_table_header_window(lines: List[str], i: int) -> bool:
    window = _norm(" ".join(lines[i:i + 90]))
    has_title = any(t in window for t in TITLE_TOKENS)
    if not has_title:
        return False

    # Este estado suele repetir S/000 varias veces en el header.
    if window.count("s/000") < 3:
        return False

    body = _norm(" ".join(lines[i:i + 180]))
    body_hits = sum(1 for s in BODY_SIGNALS if s in body)
    return body_hits >= 2


def _extract_unit(lines: List[str], i: int) -> str:
    return "S/000"


def _extract_table_title(lines: List[str], start_idx: int) -> str:
    candidates = []
    for j in range(max(0, start_idx - 16), min(len(lines), start_idx + 10)):
        ln = lines[j].strip()
        if not ln:
            continue
        low = _norm(ln)
        if low.startswith("por los anos terminados"):
            continue
        if "s/000" in low:
            continue
        if YEAR_RE.match(ln):
            continue
        if "nota" == low:
            continue
        candidates.append(ln)

    for c in candidates:
        if "PATRIMONIO NETO" in c.upper():
            return c
    return candidates[-1] if candidates else "Estado de cambios en el patrimonio neto"


def _match_row_at(lines: List[str], i: int, max_lines: int = 3) -> Optional[Tuple[str, int]]:
    parts: List[str] = []
    for span in range(1, max_lines + 1):
        if i + span - 1 >= len(lines):
            break
        piece = lines[i + span - 1].strip()
        if not piece:
            break
        parts.append(piece)
        candidate = " ".join(parts).strip()

        for label in ROW_LABELS:
            if _norm(candidate) == _norm(label):
                return label, i + span

    return None


def _consume_header(lines: List[str], start_idx: int) -> int:
    i = start_idx
    limit = min(len(lines), start_idx + 120)
    while i < limit:
        if _match_row_at(lines, i):
            return i
        i += 1
    return i


def _read_value_sequence(lines: List[str], i: int, max_values: int = 14) -> Tuple[List[str], int]:
    values: List[str] = []
    while i < len(lines) and len(values) < max_values:
        ln = lines[i].strip()

        if not ln:
            i += 1
            continue

        if _looks_like_table_header_window(lines, i):
            break
        if _match_row_at(lines, i):
            break
        if "las notas que se acompanan" in _norm(ln):
            break

        # Admite "-" como celda vacia explicita
        if ln == "-":
            values.append(ln)
            i += 1
            continue

        if not is_numericish(ln):
            break

        values.append(ln)
        i += 1

    return values, i


def extract_financial_statements_tables_family_4(page_record: dict) -> List[Dict]:
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

        table_start = i
        unit = _extract_unit(lines, i)
        title = _extract_table_title(lines, i)
        cursor = _consume_header(lines, i)

        rows: List[Dict] = []

        while cursor < len(lines):
            ln = lines[cursor].strip()

            if not ln:
                cursor += 1
                continue

            if _looks_like_table_header_window(lines, cursor):
                break

            if "las notas que se acompanan" in _norm(ln):
                break

            row_match = _match_row_at(lines, cursor)
            if not row_match:
                if len(ln.split()) >= 10 and not is_numericish(ln):
                    break
                cursor += 1
                continue

            metric, cursor = row_match

            values, cursor = _read_value_sequence(lines, cursor, max_values=14)
            if not values:
                continue

            rows.append(
                {
                    "metric": metric,
                    "values": values,
                }
            )

        table_end = cursor
        if table_end > table_start and rows:
            page_record.setdefault("table_ranges", []).append((table_start, table_end))

        if rows:
            reconstructed_lines = [
                f"TABLA CAMBIOS EN PATRIMONIO | Título: {title} | Unidad: {unit}"
            ]
            for r in rows:
                reconstructed_lines.append(
                    f"{r['metric']} | Valores: {' | '.join(r['values'])}"
                )

            tables.append(
                {
                    "table_type": 10,
                    "title": title,
                    "unit": unit,
                    "rows": rows,
                    "reconstructed_text": "\n".join(reconstructed_lines),
                }
            )

        i = cursor if cursor > i else i + 1

    return tables
