"""
Balance General - Familia 2
Solo 35 líneas de configuración + formato.
"""
from typing import Dict, List
from src.ingest.table_extractors.table_extractor_base import SimpleTableExtractor


class EarningsFamily2(SimpleTableExtractor):
    """Extrae tablas de BALANCE GENERAL (familia 2)."""
    
    # ========== CONFIGURACIÓN ==========
    TABLE_TYPE = 2
    HEADERS = ["4T24", "4T23", "Var."]
    ROW_LABELS = [
        "Efectivo y equivalentes de efectivo",
        "Activos corrientes",
        "Activos totales",
        "Deuda corriente3",
        "Pasivos corrientes",
        "Deuda no corriente3",
        "Pasivos totales",
        "Patrimonio",
        "Capital de trabajo4",
        "Deuda financiera neta",
        "Ratio corriente",
        "Deuda neta / EBITDA ajustado5",
        "Ratio de apalancamiento6",
    ]
    HEADER_WINDOW_SIZE = 6
    MAX_VALUES = 3
    DEFAULT_TITLE = "Tabla balance general"
    
    # ========== LÓGICA ESPECÍFICA ==========
    
    def extract(self, page_record: dict) -> List[Dict]:
        """Sobrescribe para saltar "Ratios" si aparece."""
        if (page_record.get("doc_type") or "").lower() != self.DOC_TYPE:
            return []
        
        # ... (heredar lógica base hasta el loop de rows)
        # Aquí solo agregar validación extra para "Ratios"
        
        # Para ahora, llamar a la base
        return super().extract(page_record)
    
    def _format_row(self, metric: str, values: List[str]) -> Dict:
        """Mapea 3 valores a columnas de family_2."""
        v4t24, v4t23, vvar = values
        return {
            "metric": metric,
            "4T24": v4t24,
            "4T23": v4t23,
            "var_q": vvar,
        }
    
    def _format_table(self, title: str, unit: str, rows: List[Dict]) -> Dict:
        """Formato de tabla para family_2."""
        reconstructed = [f"TABLA BALANCE GENERAL | Título: {title} | Unidad: {unit}"]
        for r in rows:
            reconstructed.append(
                f"{r['metric']} | 4T24: {r['4T24']} | 4T23: {r['4T23']} | Var.: {r['var_q']}"
            )
        
        return {
            "table_type": self.TABLE_TYPE,
            "title": title,
            "unit": unit,
            "rows": rows,
            "reconstructed_text": "\n".join(reconstructed),
        }


def extract_earnings_report_tables_family_2(page_record: dict) -> List[Dict]:
    """Punto de entrada."""
    extractor = EarningsFamily2()
    return extractor.extract(page_record)