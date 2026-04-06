from src.ingest.table_extractors.earnings_reports.family_1 import extract_earnings_report_tables_from_page
from typing import List, Dict

def table_content_extractor(page_content: dict) -> List[Dict]:
    tables: List[Dict] = []
    if (page_content.get("doc_type") or "").lower() == "earnings_reports":
        tables = extract_earnings_report_tables_from_page(page_content)
    return tables
