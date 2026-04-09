from src.ingest.table_extractors.earnings_reports.family_1 import extract_earnings_report_tables_family_1
from src.ingest.table_extractors.earnings_reports.family_2 import extract_earnings_report_tables_family_2
from src.ingest.table_extractors.earnings_reports.family_3 import extract_earnings_report_tables_family_3
from src.ingest.table_extractors.earnings_reports.family_4 import extract_earnings_report_tables_family_4
from src.ingest.table_extractors.earnings_reports.family_5 import extract_earnings_report_tables_family_5
from src.ingest.table_extractors.earnings_reports.family_6 import extract_earnings_report_tables_family_6
from typing import Callable, List, Dict

def table_content_extractor(page_content: dict) -> List[Dict]:
    if (page_content.get("doc_type") or "").lower() != "earnings_reports":
        return []

    extractors: List[Callable[[dict], List[Dict]]] = [
        extract_earnings_report_tables_family_1,
        extract_earnings_report_tables_family_2,
        extract_earnings_report_tables_family_3,
        extract_earnings_report_tables_family_4,
        extract_earnings_report_tables_family_5,
        extract_earnings_report_tables_family_6,
    ]

    for extractor in extractors:
        tables = extractor(page_content)
        if tables:
            return tables

    return []