from typing import Dict, List, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish

IS_TABLE_HEADERS = [
    "notes",
    "trimestre del 1 de octubre al 31 de diciembre de 2024",
    "trimestre del 1 de octubre al 31 de diciembre de 2023",
    "periodo del 1 de enero al 31 de diciembre de 2024",
    "periodo del 1 de enero al 31 de diciembre de 2023",
]

IS_ROW_LABELS = [
    "Ingresos de Actividades Ordinarias",
    "Costo de Ventas",
    "Ganancia (Pérdida) Bruta",
    "Gastos de Ventas y Distribución",
    "Gastos de Administración",
    "Otros Ingresos Operativos",
    "Otros Gastos Operativos",
    "Otras Ganancias (Pérdidas)",
    "Ganancia (Pérdida) Operativa",
    "Ingresos Financieros",
    "Gastos Financieros",
    "Diferencias de Cambio Neto",
    "Participación en los Resultados de Asociadas",
    "Ganancia (Pérdida) antes de Impuestos",
    "Ingreso (Gasto) por Impuesto",
    "Ganancia (Pérdida) Neta de Operaciones Continuadas",
    "Ganancia (Pérdida) de Operaciones Discontinuadas",
    "Ganancia (Pérdida) Neta del Ejercicio",
    "Básica por Acción Ordinaria en Operaciones Continuas",
    "Básica por Acción de Inversión en Operaciones Continuas",
    "Básica por Acción Ordinaria en Operaciones Discontinuadas",
    "Básica por Acción de Inversión en Operaciones Discontinuadas",
    "Total de Ganancias (Pérdida) Básica por Acción Ordinaria",
    "Total de Ganancias (Pérdida) Básica por Acción Inversión",
    "Diluida por Acción Ordinaria en Operaciones Continuas",
    "Diluida por Acción de Inversión en Operaciones Continuas",
    "Diluida por Acción Ordinaria en Operaciones Discontinuadas",
    "Diluida por Acción de Inversión en Operaciones Discontinuadas",
    "Total ganancias (Pérdida) Diluida por Acción Ordinaria",
    "Total de Ganancias (Pérdida) Diluida por Acción Inversión",
]

IS_SECTION_ROWS = [
    "Ganancias (Pérdida) Básica por Acción:",
    "Ganancias (Pérdida) Diluida por Acción:",
]

IS_ROW_LABELS = sorted(IS_ROW_LABELS, key=len, reverse=True)
IS_ROW_LABELS_SET = set(IS_ROW_LABELS)
IS_SECTION_ROWS_SET = set(IS_SECTION_ROWS)


def _norm_inline(s: str) -> str:
    return " ".join(s.split()).strip()


def _looks_like_table_header_window(lines: List[str], i: int) -> bool:
    # Encabezado viene cortado en muchas líneas; por eso usamos una ventana amplia y normalizada
    window = _norm_inline(" ".join(lines[i:i + 40])).lower()
    return all(token in window for token in IS_TABLE_HEADERS)


def _extract_unit(lines: List[str], i: int) -> str:
    for j in range(max(0, i - 8), min(len(lines), i + 8)):
        low = lines[j].lower()
        if "miles de soles" in low:
            return "miles de soles"
    return "unidad no identificada"


def _extract_table_title(lines: List[str], start_idx: int) -> str:
    candidates = []
    for j in range(max(0, start_idx - 8), start_idx):
        ln = lines[j].strip()
        if not ln:
            continue
        low = ln.lower()
        if low.startswith("por los periodos terminados"):
            continue
        if "miles de soles" in low:
            continue
        candidates.append(ln)

    if not candidates:
        return "Estado de resultados consolidado"
    return candidates[-1]


def _consume_header(lines: List[str], start_idx: int) -> int:
    # Avanza hasta encontrar la primera fila conocida
    i = start_idx
    limit = min(len(lines), start_idx + 60)
    while i < limit:
        if _match_metric_at(lines, i) is not None:
            return i
        i += 1
    return i


def _match_metric_at(lines: List[str], i: int) -> Tuple[str, int] | None:
    # Soporta métricas en 1, 2 o 3 líneas (ej: "... Operaciones" + "Continuadas")
    if i >= len(lines):
        return None

    parts = []
    for span in range(1, 4):
        if i + span - 1 >= len(lines):
            break
        part = lines[i + span - 1].strip()
        if not part:
            break
        parts.append(part)
        candidate = _norm_inline(" ".join(parts))

        if candidate in IS_ROW_LABELS_SET:
            return candidate, i + span
        if candidate in IS_SECTION_ROWS_SET:
            return candidate, i + span

    return None


def _read_value_sequence(lines: List[str], i: int, max_values: int = 5) -> Tuple[List[str], int]:
    values = []
    while i < len(lines) and len(values) < max_values:
        ln = lines[i].strip()

        if not ln:
            i += 1
            continue

        if _looks_like_table_header_window(lines, i):
            break

        if _match_metric_at(lines, i) is not None:
            break

        if not is_numericish(ln):
            break

        values.append(ln)
        i += 1

    return values, i


def _pad_values(values: List[str], n: int = 5) -> List[str]:
    vals = values[:]
    while len(vals) < n:
        vals.append("-")
    return vals[:n]


def extract_earnings_report_tables_family_3(page_record: dict) -> List[Dict]:
    if (page_record.get("doc_type") or "").lower() != "earnings_reports":
        return []

    text = (page_record.get("page_text") or "").strip()
    if not text:
        return []

    lines = normalize_lines(text)
    tables = []
    i = 0

    while i < len(lines):
        if _looks_like_table_header_window(lines, i):
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

                if _looks_like_table_header_window(lines, cursor):
                    break

                metric_match = _match_metric_at(lines, cursor)
                if metric_match is None:
                    if len(ln.split()) >= 6 and not is_numericish(ln):
                        break
                    cursor += 1
                    continue

                metric, next_cursor = metric_match
                cursor = next_cursor

                if metric in IS_SECTION_ROWS_SET:
                    continue

                values, cursor = _read_value_sequence(lines, cursor, max_values=5)
                if not values:
                    continue

                note, q4_2024, q4_2023, y_2024, y_2023 = _pad_values(values, 5)
                rows.append({
                    "metric": metric,
                    "note": note,
                    "q4_2024": q4_2024,
                    "q4_2023": q4_2023,
                    "y_2024": y_2024,
                    "y_2023": y_2023,
                })

            table_end = cursor
            if table_end > table_start:
                page_record.setdefault("table_ranges", []).append((table_start, table_end))

            if rows:
                reconstructed_lines = [
                    f"TABLA ESTADO RESULTADOS CONSOLIDADO | Título: {title} | Unidad: {unit}"
                ]
                for r in rows:
                    reconstructed_lines.append(
                        f"{r['metric']} | Nota: {r['note']} | "
                        f"Trimestre 2024: {r['q4_2024']} | Trimestre 2023: {r['q4_2023']} | "
                        f"Periodo 2024: {r['y_2024']} | Periodo 2023: {r['y_2023']}"
                    )

                tables.append({
                    "table_type": 3,
                    "title": title,
                    "unit": unit,
                    "rows": rows,
                    "reconstructed_text": "\n".join(reconstructed_lines),
                })

            i = cursor if cursor > i else i + 1
            continue

        i += 1

    return tables