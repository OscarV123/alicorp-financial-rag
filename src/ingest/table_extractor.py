import re
from typing import Iterator, Optional, Tuple

TABLE_HEADERS_COMMON = [
    "cantidad", "monto", "importe", "total",
    "porcentaje", "percent", "%",
    "fecha", "date",
    "precio", "price",
    "unidad", "units",
    "tasa", "rate",
    "saldo", "balance",
    "ingresos", "revenue", "ventas",
    "costo", "cost", "costos",
    "gastos", "expenses",
    "activo", "assets",
    "pasivo", "liabilities",
    "patrimonio", "equity",
    "deuda", "debt",
    "s/", "soles", "usd", "$", "eur",
    "ebitda", "utilidad", "neto", "gross",
    "\t"
]

NOTE_CUT_RE = re.compile(r"\bnota\s*:\b|\bobservaci[oó]n\s*:\b", re.IGNORECASE)

DATE_PAT = r"\d{1,2}[-/][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,9}[-/]\d{2,4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"

def normalize_for_table(text: str) -> str:
    if not text:
        return ""
    text = NOTE_CUT_RE.split(text)[0]
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text

def find_table_region(text: str, headers: list[str], window: int = 900, min_hits: int = 3) -> Optional[Tuple[int, int]]:
    if not text:
        return None

    t_lower = re.sub(r"\s+", " ", text.lower()).strip()
    if not t_lower:
        return None

    best = None
    best_score = 0
    step = 200

    for start in range(0, len(t_lower), step):
        end = min(start + window, len(t_lower))
        chunk = t_lower[start:end]

        hits = sum(1 for h in headers if h in chunk)
        nums = len(re.findall(r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?", chunk))
        score = hits * 10 + nums

        if hits >= min_hits and score > best_score:
            best_score = score
            best = (start, end)

    return best

def crop_to_table_region(text_norm: str, window: int, min_hits: int) -> str:
    region = find_table_region(text_norm, TABLE_HEADERS_COMMON, window=window, min_hits=min_hits)
    if region:
        return text_norm[region[0]:region[1]].strip()
    return text_norm

def looks_like_table(text: str) -> bool:
    if not text:
        return False

    t = text.lower()
    tokens = re.findall(r"\S+", t)
    if not tokens:
        return False

    num_tokens = len(re.findall(r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?", t))
    numbers_ratio = num_tokens / max(len(tokens), 1)
    has_enough_numbers = numbers_ratio > 0.12

    header_hits = sum(1 for h in TABLE_HEADERS_COMMON if h in t)
    has_dates = len(re.findall(r"\b\d{1,2}[-/][a-z]{3,9}[-/]\d{2,4}\b", t)) >= 2

    return (header_hits >= 3 and has_enough_numbers) or (has_dates and header_hits >= 2)

def extract_table_rows(page_record: dict) -> Iterator[dict]:
    text = normalize_for_table((page_record.get("page_text") or ""))
    if not text:
        return

    text = crop_to_table_region(text, window=1200, min_hits=3)

    doc_type = (page_record.get("doc_type") or "").lower()
    allow_row_parsing = (doc_type == "important_facts")

    if allow_row_parsing:
        row_re = re.compile(
            rf"(?:(?P<date>{DATE_PAT})\s+)?"
            r"(?P<qty>\d{1,3}(?:,\d{3})+|\d+)\s+"
            r"(?P<pct>\d+(?:\.\d+)?)%\s+"
            r"(?P<cur1>S/|USD|US\$|\$)\s*"
            r"(?P<price>\d+(?:\.\d+)?)\s+"
            r"(?P<cur2>S/|USD|US\$|\$)\s*"
            r"(?P<amt>\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+(?:\.\d{2})?)",
            flags=re.IGNORECASE,
        )

        matches = list(row_re.finditer(text))
        if len(matches) >= 3:
            last_date = None
            row_i = 0
            for m in matches:
                if m.group("date"):
                    last_date = m.group("date")
                if not last_date:
                    continue

                row_i += 1
                qty, pct = m.group("qty"), m.group("pct")
                cur1, price = m.group("cur1"), m.group("price")
                cur2, amt = m.group("cur2"), m.group("amt")

                yield {
                    **{k: v for k, v in page_record.items() if k != "page_text"},
                    "chunk_id": f"{page_record['doc_id']}_p{page_record['page_number']:03d}_trow_{row_i:03d}",
                    "chunk_type": "table_fact_row",
                    "table_detected": True,
                    "chunk_text": f"Fila tabla | Fecha: {last_date} | Cantidad: {qty} | Porcentaje: {pct}% | Precio: {cur1} {price} | Monto: {cur2} {amt}",
                    "table_row_date": last_date,
                    "table_row_qty": qty,
                    "table_row_pct": f"{pct}%",
                    "table_row_price": f"{cur1} {price}",
                    "table_row_amount": f"{cur2} {amt}",
                }
            return

    parts = re.split(f"(?=({DATE_PAT}))", text)
    seg_i = 0
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(re.findall(r"\d", p)) < 8:
            continue
        seg_i += 1
        yield {
            **{k: v for k, v in page_record.items() if k != "page_text"},
            "chunk_id": f"{page_record['doc_id']}_p{page_record['page_number']:03d}_tseg_{seg_i:03d}",
            "chunk_type": "table_segment",
            "table_detected": True,
            "chunk_text": f"Tabla | Segmento {seg_i} | {p}",
        }

def extract_table_fact_total(page_record: dict) -> Optional[dict]:
    doc_type = (page_record.get("doc_type") or "").lower()
    if doc_type != "important_facts":
        return None

    text = normalize_for_table((page_record.get("page_text") or ""))
    if not text:
        return None

    text = crop_to_table_region(text, window=1600, min_hits=2)

    qty_pat = r"(?:\d{1,3}(?:,\d{3})+|\d{4,})"
    amt_pat = r"(?:\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d{4,}(?:\.\d{2})?)"

    m = re.search(
        rf"\btotal\b[^\d]{{0,40}}(?P<qty>{qty_pat}).{{0,80}}"
        rf"(?P<cur>s/|usd|us\$|\$|eur)\s*(?P<amt>{amt_pat})",
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        return None

    qty = m.group("qty")
    cur_raw = m.group("cur").upper()
    cur = "USD" if cur_raw in ("US$", "USD") else cur_raw
    amt = m.group("amt")

    return {
        **{k: v for k, v in page_record.items() if k != "page_text"},
        "chunk_id": f"{page_record['doc_id']}_p{page_record['page_number']:03d}_ttotal_001",
        "chunk_type": "table_fact_total",
        "table_detected": True,
        "chunk_text": f"Tabla | TOTAL | Cantidad total: {qty} | Monto total: {cur} {amt}",
        "table_total_qty": qty,
        "table_total_amount": f"{cur} {amt}",
    }
