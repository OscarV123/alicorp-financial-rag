"""
Earnings Report - Familia 1
Solo 35 líneas de configuración + formato.
"""
from typing import Dict, List
from src.ingest.table_extractors.table_extractor_base import SimpleTableExtractor


class EarningsFamily1(SimpleTableExtractor):
    """Extrae tablas de EARNINGS REPORT (familia 1)."""
    
    # ========== CONFIGURACIÓN ==========
    TABLE_TYPE = 1
    HEADERS = ["4T24", "4T23", "Var. AaA", "Año '24", "Año '23", "Var. AaA"]
    ROW_LABELS = [
        "Volumen (miles de TM)",
        "Ventas netas",
        "Utilidad bruta ajustada",
        "Margen bruto ajustado",
        "Utilidad bruta ajustada por TM",
        "EBITDA ajustado",
        "Margen EBITDA ajustado",
        "EBITDA ajustado por TM",
        "EBITDA reportado",
        "Deterioro de activos intangibles",
        "Deterioro de activos fijos",
        "Gastos de reestructuración",
        "Gastos de M&A",
        "Gastos tributarios extraordinarios",
        "Desvalorización de inventarios",
        "Ganancia por venta de predios",
    ]
    HEADER_WINDOW_SIZE = 8
    MAX_VALUES = 6
    DEFAULT_TITLE = "Tabla earnings report"
    
    # ========== FORMATO ESPECÍFICO ==========
    
    def _format_row(self, metric: str, values: List[str]) -> Dict:
        """Mapea 6 valores a columnas de family_1."""
        v4t24, v4t23, vvar_q, vya24, vya23, vvar_y = values
        return {
            "metric": metric,
            "4T24": v4t24,
            "4T23": v4t23,
            "var_aa_q": vvar_q,
            "year_24": vya24,
            "year_23": vya23,
            "var_aa_y": vvar_y,
        }
    
    def _format_table(self, title: str, unit: str, rows: List[Dict]) -> Dict:
        """Formato de tabla para family_1."""
        reconstructed = [f"TABLA EARNINGS REPORT | Título: {title} | Unidad: {unit}"]
        for r in rows:
            reconstructed.append(
                f"{r['metric']} | 4T24: {r['4T24']} | 4T23: {r['4T23']} | "
                f"Var. AaA Trimestre: {r['var_aa_q']} | "
                f"Año 2024: {r['year_24']} | Año 2023: {r['year_23']} | "
                f"Var. AaA Año: {r['var_aa_y']}"
            )
        
        return {
            "table_type": self.TABLE_TYPE,
            "title": title,
            "unit": unit,
            "rows": rows,
            "reconstructed_text": "\n".join(reconstructed),
        }


def extract_earnings_report_tables_family_1(page_record: dict) -> List[Dict]:
    """Punto de entrada."""
    extractor = EarningsFamily1()
    return extractor.extract(page_record)