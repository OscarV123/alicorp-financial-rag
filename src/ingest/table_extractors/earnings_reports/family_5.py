from typing import Dict, List, Optional, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish


CF_HEADER_TOKENS = [
    "notas",
    "del 1 de enero de 2024 al 31 de diciembre de 2024",
    "del 1 de enero de 2023 al 31 de diciembre de 2023",
]

CF_SECTION_ROWS = [
    "FLUJO DE EFECTIVO DE ACTIVIDADES DE OPERACIÓN",
    "FLUJO DE EFECTIVO DE ACTIVIDADES DE INVERSIÓN",
    "FLUJO DE EFECTIVO DE ACTIVIDADES DE FINANCIACIÓN",
]

CF_SUBSECTION_ROWS = [
    "Cobros provenientes de (debido a):",
    "Pagos a (debido a):",
]

CF_ROW_LABELS = [
    "Venta de Bienes y Prestación de Servicios",
    "Otros Cobros de Efectivo",
    "Proveedores de Bienes y Servicios",
    "Salarios",
    "Impuestos a las Ganancias (Pagados)",
    "Otros Pagos de Efectivo",
    "Otros Cobros (Pagos) de Efectivo",
    "Flujos de Efectivo de Actividades de Operación",
    "Venta de Propiedades, Planta y Equipo",
    "Venta de Participaciones en Negocios Conjuntos, Neto del Efectivo Desapropiado",
    "Intereses Recibidos",
    "Venta de Activos Intangibles",
    "Compra de Subsidiarias, Neto del Efectivo Adquirido",
    "Compra de Propiedades, Planta y Equipo",
    "Compra de Activos Intangibles",
    "Impuesto a la Renta",
    "Flujos de Efectivo de Actividades de Inversión",
    "Obtención de Préstamos",
    "Amortización o Pago de Préstamos",
    "Arrendamiento Financiero",
    "Recompra de acciones",
    "Dividendos Pagados",
    "Intereses Pagados",
    "Flujos de Efectivo de Actividades de Financiación",
    "Aumento (Disminución) Neto de Efectivo, Antes de las Variaciones en las Tasas de Cambio",
    "Efectos de las Variaciones en las Tasas de Cambio sobre el Efectivo",
    "Aumento (Disminución) Neto de Efectivo",
    "Efectivo y Equivalente al Efectivo al Inicio del Ejercicio",
    "Efectivo y Equivalente al Efectivo al Finalizar el Ejercicio",
]

CF_ROW_LABELS = sorted(CF_ROW_LABELS, key=len, reverse=True)
CF_ALL_CONTROL_ROWS = set(CF_SECTION_ROWS + CF_SUBSECTION_ROWS + CF_ROW_LABELS)


def _norm(s: str) -> str:
    return " ".join(s.split()).strip()


def _looks_like_table_header_window(lines: List[str], i: int) -> bool:
    # Header viene cortado en varias líneas en OCR, por eso ventana amplia + normalización.
    window = _norm(" ".join(lines[i:i + 40])).lower()
    return all(token in window for token in CF_HEADER_TOKENS)


def _extract_unit(lines: List[str], i: int) -> str:
    for j in range(max(0, i - 8), min(len(lines), i + 8)):
        low = lines[j].lower()
        if "en miles de soles" in low:
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
        if "en miles de soles" in low:
            continue
        if low == "notas":
            continue
        candidates.append(ln)

    if not candidates:
        return "Estado de flujo de efectivo consolidado"
    return candidates[-1]


def _match_row_at(lines: List[str], i: int, labels: List[str], max_lines: int = 4) -> Optional[Tuple[str, int]]:
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
    limit = min(len(lines), start_idx + 80)
    while i < limit:
        if _match_row_at(lines, i, CF_SECTION_ROWS, max_lines=2):
            return i
        if _match_row_at(lines, i, CF_ROW_LABELS, max_lines=4):
            return i
        i += 1
    return i


def _read_note_and_values(lines: List[str], i: int) -> Tuple[str, str, str, int]:
    tokens: List[str] = []
    while i < len(lines) and len(tokens) < 3:
        ln = lines[i].strip()

        if not ln:
            i += 1
            continue

        if _looks_like_table_header_window(lines, i):
            break
        if _match_row_at(lines, i, CF_SECTION_ROWS, max_lines=2):
            break
        if _match_row_at(lines, i, CF_SUBSECTION_ROWS, max_lines=2):
            break
        if _match_row_at(lines, i, CF_ROW_LABELS, max_lines=4):
            break

        if not is_numericish(ln):
            break

        tokens.append(ln)
        i += 1

    note = "-"
    value_2024 = "-"
    value_2023 = "-"

    # Caso con nota: [nota, 2024, 2023]
    first_clean = tokens[0].replace(",", "") if tokens else ""
    if len(tokens) >= 3 and first_clean.isdigit():
        note, value_2024, value_2023 = tokens[0], tokens[1], tokens[2]
    elif len(tokens) >= 2:
        value_2024, value_2023 = tokens[0], tokens[1]
    elif len(tokens) == 1:
        value_2024 = tokens[0]

    return note, value_2024, value_2023, i


def extract_earnings_report_tables_family_5(page_record: dict) -> List[Dict]:
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
        current_section = ""
        current_subsection = ""

        while cursor < len(lines):
            ln = lines[cursor].strip()
            if not ln:
                cursor += 1
                continue

            if _looks_like_table_header_window(lines, cursor):
                break

            section_match = _match_row_at(lines, cursor, CF_SECTION_ROWS, max_lines=2)
            if section_match:
                current_section, cursor = section_match
                current_subsection = ""
                continue

            subsection_match = _match_row_at(lines, cursor, CF_SUBSECTION_ROWS, max_lines=2)
            if subsection_match:
                current_subsection, cursor = subsection_match
                continue

            metric_match = _match_row_at(lines, cursor, CF_ROW_LABELS, max_lines=4)
            if metric_match:
                metric, cursor = metric_match
                note, v2024, v2023, cursor = _read_note_and_values(lines, cursor)

                rows.append({
                    "section": current_section,
                    "subsection": current_subsection,
                    "metric": metric,
                    "note": note,
                    "value_2024": v2024,
                    "value_2023": v2023,
                })
                continue

            # Corte defensivo cuando entra texto narrativo
            if len(ln.split()) >= 8 and not is_numericish(ln):
                break

            cursor += 1

        table_end = cursor
        if table_end > table_start:
            page_record.setdefault("table_ranges", []).append((table_start, table_end))

        if rows:
            reconstructed_lines = [
                f"TABLA FLUJO EFECTIVO CONSOLIDADO | Título: {title} | Unidad: {unit}"
            ]
            for r in rows:
                reconstructed_lines.append(
                    f"{r['section']} | {r['subsection']} | {r['metric']} | Nota: {r['note']} | 2024: {r['value_2024']} | 2023: {r['value_2023']}"
                )

            tables.append({
                "table_type": 5,
                "title": title,
                "unit": unit,
                "rows": rows,
                "reconstructed_text": "\n".join(reconstructed_lines),
            })

        i = cursor if cursor > i else i + 1

    return tables
