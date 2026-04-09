from typing import Dict, List, Optional, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish


FS_HEADER_TOKENS = [
    "notas",
    "al 31 de diciembre 2024",
    "al 31 de diciembre 2023",
]

LEFT_SECTION_LABELS = {
    "Activos",
    "Activos Corrientes",
    "Activos No Corrientes",
}

RIGHT_SECTION_LABELS = {
    "Pasivos",
    "Pasivos Corrientes",
    "Pasivos No Corrientes",
    "Patrimonio",
}

LEFT_ROW_LABELS = [
    "Efectivo y Equivalentes al Efectivo",
    "Otros Activos Financieros",
    "Cuentas por Cobrar Comerciales",
    "Cuentas por Cobrar a Entidades Relacionadas",
    "Otras Cuentas por Cobrar",
    "Anticipos",
    "Inventarios",
    "Activos por Impuestos a las Ganancias",
    "Otros Activos no Financieros",
    "Disponible para venta",
    "Total Activos Corrientes",
    "Inversiones",
    "Propiedades de Inversion",
    "Propiedades, Planta y Equipo",
    "Activos Intangibles",
    "Activos por Impuestos Diferidos",
    "Activos por Impuestos Corrientes, no Corrientes",
    "Plusvalia",
    "Total Activos No Corrientes",
    "Total Activos",
]

RIGHT_ROW_LABELS = [
    "Otros Pasivos Financieros",
    "Cuentas por Pagar Comerciales",
    "Cuentas por Pagar a Entidades Relacionadas",
    "Otras Cuentas por Pagar",
    "Ingresos Diferidos",
    "Provision por Beneficios a los Empleados",
    "Provisiones",
    "Pasivos por Impuestos a las Ganancias",
    "Otros Pasivos No Financieros",
    "Total Pasivos Corrientes",
    "Pasivos por Impuestos Diferidos",
    "Pasivos por Impuestos Corrientes, no Corrientes",
    "Total Pasivos No Corrientes",
    "Total Pasivos",
    "Capital Emitido",
    "Acciones de Inversion",
    "Acciones Propias en Cartera",
    "Reservas",
    "Resultados Acumulados",
    "Otras Reservas de Patrimonio",
    "Patrimonio Atribuible a los Propietarios de la Controladora",
    "Participaciones no Controladoras",
    "Total Patrimonio",
    "Total pasivos y patrimonio",
]

LEFT_ROW_LABELS = sorted(LEFT_ROW_LABELS, key=len, reverse=True)
RIGHT_ROW_LABELS = sorted(RIGHT_ROW_LABELS, key=len, reverse=True)
ALL_SECTION_LABELS = LEFT_SECTION_LABELS.union(RIGHT_SECTION_LABELS)


def _norm(s: str) -> str:
    return " ".join(s.split()).strip()


def _looks_like_table_header_window(lines: List[str], i: int) -> bool:
    window = _norm(" ".join(lines[i:i + 50])).lower()
    return all(token in window for token in FS_HEADER_TOKENS)


def _extract_unit(lines: List[str], i: int) -> str:
    for j in range(max(0, i - 6), min(len(lines), i + 8)):
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
        if low.startswith("al cierre de"):
            continue
        if "miles de soles" in low:
            continue
        if low == "notas":
            continue
        candidates.append(ln)

    if not candidates:
        return "Estado de situacion financiera consolidado"
    return candidates[-1]


def _match_label_at(lines: List[str], i: int, labels: List[str], max_lines: int = 4) -> Optional[Tuple[str, int]]:
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


def _match_section_at(lines: List[str], i: int) -> Optional[Tuple[str, int]]:
    match = _match_label_at(lines, i, sorted(ALL_SECTION_LABELS, key=len, reverse=True), max_lines=3)
    return match


def _consume_header(lines: List[str], start_idx: int) -> int:
    i = start_idx
    limit = min(len(lines), start_idx + 80)
    while i < limit:
        if _match_section_at(lines, i):
            return i
        if _match_label_at(lines, i, LEFT_ROW_LABELS, max_lines=4):
            return i
        if _match_label_at(lines, i, RIGHT_ROW_LABELS, max_lines=4):
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
        if _match_section_at(lines, i):
            break
        if _match_label_at(lines, i, LEFT_ROW_LABELS, max_lines=4):
            break
        if _match_label_at(lines, i, RIGHT_ROW_LABELS, max_lines=4):
            break

        if not is_numericish(ln):
            break

        tokens.append(ln)
        i += 1

    note = "-"
    val_2024 = "-"
    val_2023 = "-"

    if len(tokens) >= 3 and tokens[0].replace(",", "").isdigit() and len(tokens[0]) <= 3:
        note, val_2024, val_2023 = tokens[0], tokens[1], tokens[2]
    elif len(tokens) >= 2:
        val_2024, val_2023 = tokens[0], tokens[1]
    elif len(tokens) == 1:
        val_2024 = tokens[0]

    return note, val_2024, val_2023, i


def extract_earnings_report_tables_family_4(page_record: dict) -> List[Dict]:
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
        current_left_section = ""
        current_right_section = ""

        while cursor < len(lines):
            ln = lines[cursor].strip()
            if not ln:
                cursor += 1
                continue

            if _looks_like_table_header_window(lines, cursor):
                break

            section_match = _match_section_at(lines, cursor)
            if section_match:
                section_text, next_cursor = section_match
                if section_text in LEFT_SECTION_LABELS:
                    current_left_section = section_text
                if section_text in RIGHT_SECTION_LABELS:
                    current_right_section = section_text
                cursor = next_cursor
                continue

            left_match = _match_label_at(lines, cursor, LEFT_ROW_LABELS, max_lines=4)
            if left_match:
                metric, next_cursor = left_match
                cursor = next_cursor
                note, v2024, v2023, cursor = _read_note_and_values(lines, cursor)
                rows.append({
                    "side": "activos",
                    "section": current_left_section,
                    "metric": metric,
                    "note": note,
                    "value_2024": v2024,
                    "value_2023": v2023,
                })
                continue

            right_match = _match_label_at(lines, cursor, RIGHT_ROW_LABELS, max_lines=4)
            if right_match:
                metric, next_cursor = right_match
                cursor = next_cursor
                note, v2024, v2023, cursor = _read_note_and_values(lines, cursor)
                rows.append({
                    "side": "pasivos_patrimonio",
                    "section": current_right_section,
                    "metric": metric,
                    "note": note,
                    "value_2024": v2024,
                    "value_2023": v2023,
                })
                continue

            if len(ln.split()) >= 8 and not is_numericish(ln):
                break

            cursor += 1

        table_end = cursor
        if table_end > table_start:
            page_record.setdefault("table_ranges", []).append((table_start, table_end))

        if rows:
            reconstructed_lines = [
                f"TABLA ESTADO SITUACION FINANCIERA CONSOLIDADO | Título: {title} | Unidad: {unit}"
            ]
            for r in rows:
                reconstructed_lines.append(
                    f"[{r['side']}] {r['section']} | {r['metric']} | Nota: {r['note']} | 2024: {r['value_2024']} | 2023: {r['value_2023']}"
                )

            tables.append({
                "table_type": 4,
                "title": title,
                "unit": unit,
                "rows": rows,
                "reconstructed_text": "\n".join(reconstructed_lines),
            })

        i = cursor if cursor > i else i + 1

    return tables
