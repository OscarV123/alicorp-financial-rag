from ingest.table_extractors.earnings_reports.family_1_er import extract_earnings_report_tables_family_1
from ingest.table_extractors.earnings_reports.family_2_er import extract_earnings_report_tables_family_2
from ingest.table_extractors.earnings_reports.family_3_er import extract_earnings_report_tables_family_3
from ingest.table_extractors.earnings_reports.family_4_er import extract_earnings_report_tables_family_4
from ingest.table_extractors.earnings_reports.family_5_er import extract_earnings_report_tables_family_5
from ingest.table_extractors.earnings_reports.family_6_er import extract_earnings_report_tables_family_6
from src.ingest.table_extractors.financial_statements_table_extractors.family_1 import extract_financial_statements_tables_family_1
from src.ingest.table_extractors.financial_statements_table_extractors.family_2 import extract_financial_statements_tables_family_2
from src.ingest.table_extractors.financial_statements_table_extractors.family_3 import extract_financial_statements_tables_family_3
from src.ingest.table_extractors.financial_statements_table_extractors.family_4 import extract_financial_statements_tables_family_4
from src.ingest.table_extractors.financial_statements_table_extractors.family_5 import extract_financial_statements_tables_family_5
from typing import Callable, List, Dict

def table_content_extractor(page_content: dict) -> List[Dict]:
    doc_type = (page_content.get("doc_type") or "").lower()

    extractors_by_doc_type: Dict[str, List[Callable[[dict], List[Dict]]]] = {
        "earnings_reports": [
            extract_earnings_report_tables_family_1,
            extract_earnings_report_tables_family_2,
            extract_earnings_report_tables_family_3,
            extract_earnings_report_tables_family_4,
            extract_earnings_report_tables_family_5,
            extract_earnings_report_tables_family_6,
        ],
        "financial_statements": [
            extract_financial_statements_tables_family_1,
            extract_financial_statements_tables_family_2,
            extract_financial_statements_tables_family_3,
            extract_financial_statements_tables_family_4,
            extract_financial_statements_tables_family_5,
        ],
    }

    for extractor in extractors_by_doc_type.get(doc_type, []):
        tables = extractor(page_content)
        if tables:
            return tables

    return []