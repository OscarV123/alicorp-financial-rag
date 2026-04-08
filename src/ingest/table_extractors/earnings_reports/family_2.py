from typing import Dict, List, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish

BALANCE_TABLE_HEADERS = [
    "4T24", "4T23", "Var."
]

BALANCE_ROW_LABELS = [
    "Efectivo y equivalentes de efectivo",
    "Activos corrientes",
    "Activos totales",
    "Deuda corriente3",
    "Pasivos corrientes",
    "Deuda no corriente3",
    "Pasivos totales",
    "Patrimonio",
    "Capital de trabajo4",
    "Deuda financiera neta",
    "Ratio corriente",
    "Deuda neta / EBITDA ajustado5",
    "Ratio de apalancamiento6",
]

BALANCE_ROW_LABELS = sorted(BALANCE_ROW_LABELS, key=len, reverse=True)

def _looks_like_table_header_window(lines: List[str], i: int) -> bool:
    window = " | ".join(lines[i:i + 6])
    required = ["4T24", "4T23", "Var."]
    return all(x in window for x in required)


def _looks_like_balance_header(lines: List[str], i: int) -> bool:
    window = " | ".join(lines[i:i + 6])
    required = ["4T24", "4T23"]
    return all(col in window for col in required) and "Var." in window

def _extract_unit(lines: List[str], i: int) -> str:
    for j in range(max(0, i - 3), min(len(lines), i + 2)):
        low = lines[j].lower()
        if "en millones de soles" in low:
            return "millones de soles"
        
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
        if ln in BALANCE_TABLE_HEADERS:
            continue
        candidates.append(ln)

    if not candidates:
        return "Tabla balance general"
    return candidates[-1]


def _consume_header(lines: List[str], start_idx: int) -> int:
    i = start_idx

    if i < len(lines) and lines[i].lower().startswith("en millones de"):
        i += 1

    header_tokens = ["4T24", "4T23", "Var."]
    for token in header_tokens:
        if i < len(lines) and lines[i] == token:
            i += 1

    return i


def _read_value_sequence(lines: List[str], i: int, max_values: int = 3) -> Tuple[List[str], int]:
    values = []
    while i < len(lines) and len(values) < max_values:
        ln = lines[i].strip()

        if not ln:
            i += 1
            continue

        if _looks_like_table_header_window(lines, i):
            break

        if ln in BALANCE_ROW_LABELS:
            break

        if not is_numericish(ln):
            break

        values.append(ln)
        i += 1

    return values, i


def _pad_values(values: List[str], n: int = 3) -> List[str]:
    vals = values[:]
    while len(vals) < n:
        vals.append("-")
    return vals[:n]


def extract_earnings_report_tables_family_2(page_record: dict) -> List[Dict]:
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
            lines[i].lower().startswith("en millones de")
            and i + 1 < len(lines)
            and _looks_like_table_header_window(lines, i + 1)
        ):
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
                    break

                if ln == "Ratios":
                    cursor += 1
                    continue

                if ln not in BALANCE_ROW_LABELS:
                    if len(ln.split()) >= 4 and not is_numericish(ln):
                        break
                    cursor += 1
                    continue

                metric = ln
                cursor += 1

                values, cursor = _read_value_sequence(lines, cursor, max_values=3)
                if not values:
                    continue

                v4t24, v4t23, vvar = _pad_values(values, 3)
                rows.append({
                    "metric": metric,
                    "4T24": v4t24,
                    "4T23": v4t23,
                    "var_q": vvar,
                })

            table_end = cursor
            page_record.setdefault("table_ranges", []).append((table_start, table_end))

            if rows:
                reconstructed_lines = [
                    f"TABLA BALANCE GENERAL | Título: {title} | Unidad: {unit}"
                ]
                for r in rows:
                    reconstructed_lines.append(
                        f"{r['metric']} | 4T24: {r['4T24']} | 4T23: {r['4T23']} | Var.: {r['var_q']}"
                    )

                tables.append({
                    "table_type": 2,
                    "title": title,
                    "unit": unit,
                    "rows": rows,
                    "reconstructed_text": "\n".join(reconstructed_lines),
                })

            if cursor <= i:
                i += 1
            else:
                i = cursor
            continue

        i += 1

    return tables