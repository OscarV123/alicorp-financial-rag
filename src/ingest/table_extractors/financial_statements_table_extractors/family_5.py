import re
import unicodedata
from typing import Dict, List, Optional, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish


CASHFLOW_TITLE_TOKENS = [
    "ESTADO SEPARADO DE FLUJOS DE EFECTIVO",
    "ESTADO CONSOLIDADO DE FLUJO DE EFECTIVO",
]

CASHFLOW_SECTION_ROWS = [
    "ACTIVIDADES DE OPERACIÓN:",
    "Actividades de operación",
    "ACTIVIDADES DE INVERSIÓN:",
    "Actividades de inversión",
    "ACTIVIDADES DE FINANCIAMIENTO:",
    "Actividades de financiamiento",
    "Actividades de inversión y financiamiento que no implicaron efectivo",
]

CASHFLOW_ROW_LABELS = [
    "Cobranza por ventas de productos",
    "Otros cobros relativos a las actividades de operación",
    "Pagos a proveedores de bienes y servicios",
    "Pagos a empleados",
    "Pagos del impuesto a las ganancias",
    "Cobro (pago) netos de fondo de garantía para operaciones con derivados",
    "Pago por operaciones con derivados",
    "Pagos de tributos",
    "Otros pagos relativos a las actividades de operación",
    "Cobro por recuperos relacionados al crédito fiscal de exportación de Bolivia (CEDEIM)",
    "Pagos relacionados al crédito fiscal de exportación de Bolivia",
    "Otros tributos",
    "Intereses pagados",
    "Efectivo y equivalente de efectivo provenientes de las actividades de operación",

    "Venta de propiedades, planta y equipo y activos intangibles",
    "Cobro por venta de propiedades, planta y equipo",
    "Intereses y rendimientos",
    "Intereses cobrados",
    "Aporte de capital en subsidiarias",
    "Compra de participaciones en subsidiarias",
    "Reducción de capital en inversiones",
    "Compra de propiedades, planta y equipo",
    "Compra de activos intangibles",
    "Reembolsos recibidos de préstamos a partes relacionadas",
    "Préstamos concedidos a partes relacionadas",
    "Adición de inversiones a vencimiento",
    "Cobro por venta de disposición de operaciones discontinuadas",
    "Pago por venta de disposición de operaciones discontinuadas",
    "Cobro por venta de inversiones en instrumentos de patrimonio",
    "Pago por compra de propiedades, planta y equipo",
    "Pago por compra de activos intangibles",
    "Otros cobros relativos a la actividad de inversión",
    "Efectivo y equivalente de efectivo utilizados en las actividades de inversión",
    "Efectivo y equivalente de efectivo provenientes de las actividades de inversión",

    "Préstamos recibidos de terceros a corto plazo",
    "Préstamos recibidos de terceros a largo plazo",
    "Emisión de bono corporativo",
    "Amortización de préstamos de terceros a corto plazo",
    "Amortización de préstamos de terceros a largo plazo",
    "Préstamos obtenidos de partes relacionadas",
    "Préstamos pagados a partes relacionadas",
    "Amortización de pasivos por arrendamientos",
    "Dividendos pagados",
    "Recompra de acciones",
    "Recompra de acciones propias",
    "Amortización por recompra de bonos",
    "Otros pagos relativos a la actividad de financiación",
    "Otros pagos relativos a la actividad de financiamiento",
    "Efectivo y equivalente de efectivo utilizados en las actividades de financiamiento",
    "Efectivo y equivalente de efectivo utilizados en las actividades de financiación",

    "(Disminución) Aumento neto de efectivo y equivalente al efectivo",
    "(Disminución) Aumento neto de efectivo y equivalente de efectivo",
    "Aumento neto de efectivo y equivalente de efectivo",
    "Efectivo y equivalente de efectivo al inicio del ejercicio",
    "Efecto neto de la diferencia en cambio sobre los saldos de efectivo y equivalente de efectivo en moneda extranjera",
    "Efectivo y equivalente de efectivo al final del ejercicio",

    "Adquisición de activos por derecho de uso",
    "Adquisición de activos por arrendamientos con entidades financieras",
    "Activos netos recibidos por la fusión de Vegetalia S.A.C.",
    "Acivos netos recibidos por la fusión de Vegetalia S.A.C.",
    "Bajas de activos fijos que no constituyeron venta",
    "Capitalización de cuentas por pagar a partes relacionadas",
]

CASHFLOW_ROW_LABELS = sorted(set(CASHFLOW_ROW_LABELS), key=len, reverse=True)
CASHFLOW_SECTION_ROWS = sorted(set(CASHFLOW_SECTION_ROWS), key=len, reverse=True)

YEAR_RE = re.compile(r"^20\d{2}$")
NOTE_RE = re.compile(r"^\d+(?:\.\d+)?(?:\s*\([^)]+\))*?(?:\s*y\s*\([^)]+\))*$", re.IGNORECASE)


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _norm(s: str) -> str:
    s = " ".join(s.split()).strip()
    s = _strip_accents(s).lower()
    return s


def _extract_years(lines: List[str], i: int) -> Tuple[str, str]:
    years: List[str] = []
    for ln in lines[i:i + 90]:
        tok = " ".join(ln.split()).strip()
        if YEAR_RE.match(tok) and tok not in years:
            years.append(tok)
    if len(years) >= 2:
        return years[0], years[1]
    return "year_a", "year_b"


def _looks_like_table_header_window(lines: List[str], i: int) -> bool:
    window = _norm(" ".join(lines[i:i + 80]))
    has_title = any(_norm(t) in window for t in CASHFLOW_TITLE_TOKENS)
    if not has_title:
        return False
    if "nota" not in window or "s/000" not in window:
        return False
    y1, y2 = _extract_years(lines, i)
    return y1 != "year_a" and y2 != "year_b"


def _looks_like_continuation_page(lines: List[str], i: int) -> bool:
    # Para páginas donde la tabla continúa sin repetir el título completo.
    probe = _norm(" ".join(lines[i:i + 140]))
    section_hits = sum(1 for s in CASHFLOW_SECTION_ROWS if _norm(s) in probe)
    row_hits = sum(1 for r in CASHFLOW_ROW_LABELS[:40] if _norm(r) in probe)
    return section_hits >= 1 and row_hits >= 5


def _extract_unit(lines: List[str], i: int) -> str:
    return "S/000"


def _extract_table_title(lines: List[str], start_idx: int) -> str:
    candidates = []
    for j in range(max(0, start_idx - 16), min(len(lines), start_idx + 10)):
        ln = " ".join(lines[j].split()).strip()
        if not ln:
            continue
        low = _norm(ln)
        if low.startswith("por los anos terminados") or low.startswith("por el ano terminado"):
            continue
        if low in {"nota", "s/000"}:
            continue
        if YEAR_RE.match(ln):
            continue
        candidates.append(ln)

    for c in candidates:
        cu = c.upper()
        if "ESTADO" in cu and "EFECTIVO" in cu:
            return c
    return candidates[-1] if candidates else "Estado de flujo de efectivo"


def _looks_like_note(token: str) -> bool:
    compact = " ".join(token.split()).strip()
    if NOTE_RE.match(compact):
        return True
    no_spaces = compact.replace(" ", "")
    return bool(re.match(r"^\d+(?:\.\d+)?(?:\([^)]+\))*?(?:y\([^)]+\))*$", no_spaces, re.IGNORECASE))


def _match_label_at(lines: List[str], i: int, labels: List[str], max_lines: int = 5) -> Optional[Tuple[str, int, str]]:
    parts: List[str] = []
    for span in range(1, max_lines + 1):
        if i + span - 1 >= len(lines):
            break
        piece = lines[i + span - 1].strip()
        if not piece:
            break
        parts.append(piece)
        candidate = " ".join(parts).strip()
        candidate_norm = _norm(candidate)

        for label in labels:
            label_norm = _norm(label)
            if candidate_norm == label_norm:
                return label, i + span, "-"
            if candidate_norm.startswith(label_norm + " "):
                tail = candidate[len(label):].strip()
                if _looks_like_note(tail):
                    return label, i + span, tail
    return None


def _consume_header(lines: List[str], start_idx: int) -> int:
    i = start_idx
    limit = min(len(lines), start_idx + 120)
    while i < limit:
        if _match_label_at(lines, i, CASHFLOW_SECTION_ROWS, max_lines=3):
            return i
        if _match_label_at(lines, i, CASHFLOW_ROW_LABELS, max_lines=5):
            return i
        i += 1
    return i


def _read_note_and_values(lines: List[str], i: int, inline_note: str = "-") -> Tuple[str, str, str, int]:
    note = inline_note if inline_note and inline_note != "-" else "-"
    val_a = "-"
    val_b = "-"

    while i < len(lines) and not lines[i].strip():
        i += 1

    if note == "-" and i < len(lines) and _looks_like_note(lines[i].strip()):
        note = " ".join(lines[i].split()).strip()
        i += 1

    values: List[str] = []
    while i < len(lines) and len(values) < 2:
        ln = lines[i].strip()

        if not ln:
            i += 1
            continue

        if _looks_like_table_header_window(lines, i):
            break
        if _match_label_at(lines, i, CASHFLOW_SECTION_ROWS, max_lines=3):
            break
        if _match_label_at(lines, i, CASHFLOW_ROW_LABELS, max_lines=5):
            break
        if "las notas que se acompanan" in _norm(ln):
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


def extract_financial_statements_tables_family_5(page_record: dict) -> List[Dict]:
    if (page_record.get("doc_type") or "").lower() != "financial_statements":
        return []

    text = (page_record.get("page_text") or "").strip()
    if not text:
        return []

    lines = normalize_lines(text)
    tables: List[Dict] = []
    i = 0

    while i < len(lines):
        starts_here = _looks_like_table_header_window(lines, i) or _looks_like_continuation_page(lines, i)
        if not starts_here:
            i += 1
            continue

        year_a, year_b = _extract_years(lines, i)
        if year_a == "year_a":
            # fallback razonable para páginas continuadas
            y = int(page_record.get("year") or 0)
            if y > 0:
                year_a, year_b = str(y), str(y - 1)

        table_start = i
        unit = _extract_unit(lines, i)
        title = _extract_table_title(lines, i)
        cursor = _consume_header(lines, i)

        rows: List[Dict] = []
        current_section = "Actividades de operación"

        while cursor < len(lines):
            ln = lines[cursor].strip()

            if not ln:
                cursor += 1
                continue

            if _looks_like_table_header_window(lines, cursor):
                break

            if "las notas que se acompanan" in _norm(ln):
                break

            sec_match = _match_label_at(lines, cursor, CASHFLOW_SECTION_ROWS, max_lines=3)
            if sec_match:
                current_section, cursor, _ = sec_match
                continue

            metric_match = _match_label_at(lines, cursor, CASHFLOW_ROW_LABELS, max_lines=5)
            if not metric_match:
                # no cortamos agresivo: avanzamos para no truncar por OCR raro
                cursor += 1
                continue

            metric, cursor, inline_note = metric_match
            note, v_a, v_b, cursor = _read_note_and_values(lines, cursor, inline_note=inline_note)

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
                f"TABLA FLUJO DE EFECTIVO | Título: {title} | Unidad: {unit} | Años: {year_a}, {year_b}"
            ]
            for r in rows:
                reconstructed_lines.append(
                    f"{r['section']} | {r['metric']} | Nota: {r['note']} | {year_a}: {r['year_a']} | {year_b}: {r['year_b']}"
                )

            tables.append(
                {
                    "table_type": 11,
                    "title": title,
                    "unit": unit,
                    "years": [year_a, year_b],
                    "rows": rows,
                    "reconstructed_text": "\n".join(reconstructed_lines),
                }
            )

        i = cursor if cursor > i else i + 1

    return tables
