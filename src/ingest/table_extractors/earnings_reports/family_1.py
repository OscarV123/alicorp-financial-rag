import re
from typing import List, Dict, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish, remove_table_lines


EARNINGS_TABLE_HEADERS = [
    "4T24", "4T23", "Var. AaA",
    "Año '24", "Año '23", "Var. AaA"
]

EARNINGS_ROW_LABELS = [
    "Volumen (miles de TM)",
    "Ventas netas",
    "Utilidad bruta ajustada",
    "Margen bruto ajustado",
    "Utilidad bruta ajustada por TM",
    "EBITDA ajustado",
    "Margen EBITDA ajustado",
    "EBITDA ajustado por TM",
    "EBITDA reportado",
    "Deterioro de activos intangibles",
    "Deterioro de activos fijos",
    "Gastos de reestructuración",
    "Gastos de M&A",
    "Gastos tributarios extraordinarios",
    "Desvalorización de inventarios",
    "Ganancia por venta de predios",
]

EARNINGS_ROW_LABELS = sorted(EARNINGS_ROW_LABELS, key=len, reverse=True)

def _looks_like_table_header_window(lines: List[str], i: int) -> bool:
    window = " | ".join(lines[i:i+8])
    required = ["4T24", "4T23", "Año '24", "Año '23"]
    return all(x in window for x in required)


def _extract_unit(lines: List[str], i: int) -> str:
    for j in range(max(0, i - 3), min(len(lines), i + 2)):
        low = lines[j].lower()
        if "en millones de soles" in low:
            return "millones de soles"
        if "en millones de dólares" in low or "en millones de dolares" in low:
            return "millones de dólares"
    return "unidad no identificada"


def _extract_table_title(lines: List[str], start_idx: int) -> str:
    candidates = []
    for j in range(max(0, start_idx - 5), start_idx):
        ln = lines[j].strip()
        if not ln:
            continue
        low = ln.lower()

        if low.startswith("en millones de"):
            continue
        if ln in EARNINGS_TABLE_HEADERS:
            continue
        if len(ln) > 2:
            candidates.append(ln)

    if not candidates:
        return "Tabla earnings report"

    return candidates[-1]


def _consume_header(lines: List[str], start_idx: int) -> int:
    i = start_idx

    if i < len(lines) and lines[i].lower().startswith("en millones de"):
        i += 1

    header_tokens = ["4T24", "4T23", "Var. AaA", "Año '24", "Año '23", "Var. AaA"]
    for token in header_tokens:
        if i < len(lines) and lines[i] == token:
            i += 1

    return i


def _read_value_sequence(lines: List[str], i: int, max_values: int = 6) -> Tuple[List[str], int]:
    values = []
    while i < len(lines) and len(values) < max_values:
        ln = lines[i].strip()

        if not ln:
            i += 1
            continue

        if _looks_like_table_header_window(lines, i):
            break

        if ln in EARNINGS_ROW_LABELS:
            break

        if not is_numericish(ln):
            break

        values.append(ln)
        i += 1

    return values, i


def _pad_values(values: List[str], n: int = 6) -> List[str]:
    vals = values[:]
    while len(vals) < n:
        vals.append("-")
    return vals[:n]


def extract_earnings_report_tables_from_page(page_record: dict) -> List[Dict]:
    if (page_record.get("doc_type") or "").lower() != "earnings_reports":
        return []

    text = (page_record.get("page_text") or "").strip()
    if not text:
        return []

    lines = normalize_lines(text)
    tables = []

    i = 0

    while i < len(lines):
        if _looks_like_table_header_window(lines, i) or (
            lines[i].lower().startswith("en millones de") and
            i + 1 < len(lines) and
            _looks_like_table_header_window(lines, i + 1)
        ):
            # Reconocí que esto es una tabla
            table_start = i
            
            unit = _extract_unit(lines, i)
            title = _extract_table_title(lines, i)
            cursor = _consume_header(lines, i)

            rows = []

            while cursor < len(lines):
                ln = lines[cursor].strip()

                if not ln:
                    cursor += 1
                    continue

                if _looks_like_table_header_window(lines, cursor) or (
                    lines[cursor].lower().startswith("en millones de")
                    and cursor + 1 < len(lines)
                    and _looks_like_table_header_window(lines, cursor + 1)
                ):
                    break # Si encuentro otro encabezado, asumo que es el fin de la tabla actual

                if ln not in EARNINGS_ROW_LABELS:
                    if len(ln.split()) >= 4 and not is_numericish(ln):
                        break # Si encuentro una línea que parece un título o sección nueva, asumo que es el fin de la tabla actual
                    cursor += 1
                    continue

                metric = ln
                cursor += 1

                values, cursor = _read_value_sequence(lines, cursor, max_values=6)
                if not values:
                    continue

                v4t24, v4t23, vvar_q, vya24, vya23, vvar_y = _pad_values(values, 6)

                row = {
                    "metric": metric,
                    "4T24": v4t24,
                    "4T23": v4t23,
                    "var_aa_q": vvar_q,
                    "year_24": vya24,
                    "year_23": vya23,
                    "var_aa_y": vvar_y,
                }
                rows.append(row)

            table_end = cursor
            table_ranges = page_record.setdefault("table_ranges", [])
            table_ranges.append((table_start, table_end))
            
            if rows:
                reconstructed_lines = [
                    f"TABLA EARNINGS REPORT | Título: {title} | Unidad: {unit}"
                ]

                for r in rows:
                    reconstructed_lines.append(
                        f"{r['metric']} | 4T24: {r['4T24']} | 4T23: {r['4T23']} | "
                        f"Var. AaA Trimestre: {r['var_aa_q']} | "
                        f"Año 2024: {r['year_24']} | Año 2023: {r['year_23']} | "
                        f"Var. AaA Año: {r['var_aa_y']}"
                    )

                tables.append({
                    "table_type": 1,
                    "title": title,
                    "unit": unit,
                    "rows": rows,
                    "reconstructed_text": "\n".join(reconstructed_lines),
                })

            i = cursor
            continue

        i += 1
    
    return tables

