from typing import Dict, List, Optional, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish


QTR_HEADER_TOKENS = [
    "2023",
    "2024",
    "T1",
    "T2",
    "T3",
    "T4",
    "Año",
]

QTR_ROW_LABELS = [
    "Volumen (miles TM)",
    "Ventas netas",
    "Utilidad bruta",
    "Gastos adm. y vtas.",
    "EBITDA",
    "Margen bruto",
    "GAV (% ventas)",
    "Margen EBITDA",
]

QTR_ROW_LABELS = sorted(QTR_ROW_LABELS, key=len, reverse=True)


def _norm(s: str) -> str:
    return " ".join(s.split()).strip()


def _looks_like_table_header_window(lines: List[str], i: int) -> bool:
    window = _norm(" ".join(lines[i:i + 30]))

    return all(token in window for token in QTR_HEADER_TOKENS)


def _extract_unit(lines: List[str], i: int) -> str:
    for j in range(max(0, i - 6), min(len(lines), i + 12)):
        low = lines[j].lower()
        if "millones de soles" in low:
            return "millones de soles"

    return "unidad no identificada"


def _extract_table_title(lines: List[str], start_idx: int) -> str:
    candidates = []
    for j in range(max(0, start_idx - 6), start_idx):
        ln = lines[j].strip()
        if not ln:
            continue
        low = ln.lower()
        if "millones de soles" in low:
            continue
        if ln in {"2023", "2024", "T1", "T2", "T3", "T4", "Año"}:
            continue
        candidates.append(ln)

    return candidates[-1] if candidates else "Tabla trimestral por negocio"


def _consume_header(lines: List[str], start_idx: int) -> int:
    i = start_idx
    limit = min(len(lines), start_idx + 40)
    while i < limit:
        if lines[i].strip() in QTR_ROW_LABELS:
            return i
        i += 1

    return i


def _read_value_sequence(lines: List[str], i: int, max_values: int = 10) -> Tuple[List[str], int]:
    values: List[str] = []
    while i < len(lines) and len(values) < max_values:
        ln = lines[i].strip()

        if not ln:
            i += 1
            continue

        if _looks_like_table_header_window(lines, i):
            break

        if ln in QTR_ROW_LABELS:
            break

        if not is_numericish(ln):
            break

        values.append(ln)
        i += 1

    return values, i


def _pad_values(values: List[str], n: int = 10) -> List[str]:
    vals = values[:]
    while len(vals) < n:
        vals.append("-")

    return vals[:n]


def _is_probable_new_block_start(lines: List[str], i: int) -> bool:
    ln = lines[i].strip()
    if not ln:
        return False
    if i + 1 < len(lines) and _looks_like_table_header_window(lines, i + 1):
        return True

    return len(ln.split()) >= 8 and not is_numericish(ln)


def extract_earnings_report_tables_family_6(page_record: dict) -> List[Dict]:
    if (page_record.get("doc_type") or "").lower() != "earnings_reports":
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

            if _is_probable_new_block_start(lines, cursor):
                break

            if ln not in QTR_ROW_LABELS:
                cursor += 1
                continue

            metric = ln
            cursor += 1

            values, cursor = _read_value_sequence(lines, cursor, max_values=10)
            if not values:
                continue

            (
                y2023_t1,
                y2023_t2,
                y2023_t3,
                y2023_t4,
                y2023_y,
                y2024_t1,
                y2024_t2,
                y2024_t3,
                y2024_t4,
                y2024_y,
            ) = _pad_values(values, 10)

            rows.append(
                {
                    "metric": metric,
                    "2023_t1": y2023_t1,
                    "2023_t2": y2023_t2,
                    "2023_t3": y2023_t3,
                    "2023_t4": y2023_t4,
                    "2023_year": y2023_y,
                    "2024_t1": y2024_t1,
                    "2024_t2": y2024_t2,
                    "2024_t3": y2024_t3,
                    "2024_t4": y2024_t4,
                    "2024_year": y2024_y,
                }
            )

        table_end = cursor
        if table_end > table_start:
            page_record.setdefault("table_ranges", []).append((table_start, table_end))

        if rows:
            reconstructed_lines = [
                f"TABLA INDICADORES TRIMESTRALES | Título: {title} | Unidad: {unit}"
            ]
            for r in rows:
                reconstructed_lines.append(
                    f"{r['metric']} | "
                    f"2023: T1 {r['2023_t1']} | T2 {r['2023_t2']} | T3 {r['2023_t3']} | T4 {r['2023_t4']} | Año {r['2023_year']} | "
                    f"2024: T1 {r['2024_t1']} | T2 {r['2024_t2']} | T3 {r['2024_t3']} | T4 {r['2024_t4']} | Año {r['2024_year']}"
                )

            tables.append(
                {
                    "table_type": 6,
                    "title": title,
                    "unit": unit,
                    "rows": rows,
                    "reconstructed_text": "\n".join(reconstructed_lines),
                }
            )

        i = cursor if cursor > i else i + 1

    return tables
