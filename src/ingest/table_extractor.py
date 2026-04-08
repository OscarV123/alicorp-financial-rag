from src.ingest.table_extractors.earnings_reports.family_1 import extract_earnings_report_tables_family_1
from src.ingest.table_extractors.earnings_reports.family_2 import extract_earnings_report_tables_family_2
from typing import List, Dict

def table_content_extractor(page_content: dict) -> List[Dict]:
    tables: List[Dict] = []
    if (page_content.get("doc_type") or "").lower() == "earnings_reports":
        tables = extract_earnings_report_tables_family_1(page_content)
        tables = extract_earnings_report_tables_family_2(page_content)
        
    return tables
