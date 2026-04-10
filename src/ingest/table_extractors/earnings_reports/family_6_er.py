"""
Indicadores Trimestrales - Familia 6 (Quarterly Indicators)
Múltiples tablas simples por negocio/segmento.
La MÁS SIMPLE: estructura repetitiva, sin secciones ni notas.
"""
from typing import Dict, List, Optional, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish, norm_text
from src.ingest.table_extractors.table_extractor_base import SimpleTableExtractor


class EarningsFamily6(SimpleTableExtractor):
    """Extrae tablas de INDICADORES TRIMESTRALES (familia 6)."""
    
    # ========== CONFIGURACIÓN ==========
    TABLE_TYPE = 6
    DOC_TYPE = "earnings_reports"
    
    # Headers esperados (simples, en una línea)
    HEADERS = [
        "2023",
        "2024",
        "T1",
        "T2",
        "T3",
        "T4",
        "Año",
    ]
    
    # Métricas FIJAS (siempre iguales)
    ROW_LABELS = [
        "Volumen (miles TM)",
        "Ventas netas",
        "Utilidad bruta",
        "Gastos adm. y vtas.",
        "EBITDA",
        "Margen bruto",
        "GAV (% ventas)",
        "Margen EBITDA",
    ]
    
    HEADER_WINDOW_SIZE = 30
    MAX_VALUES = 10  # T1-T4 + Año, x2 años = 10
    MAX_LINES = 1
    DEFAULT_TITLE = "Tabla trimestral por negocio"
    
    def __init__(self):
        """Inicializa set de métricas."""
        super().__init__()
        self.ROW_LABELS_SET = set(self.ROW_LABELS)
    
    # ========== OVERRIDES ESPECÍFICOS ==========
    
    def _looks_like_header(self, lines: List[str], i: int) -> bool:
        """
        Override: Headers simples, en una línea.
        Solo busca tokens clave (2023, 2024, T1-T4, Año).
        """
        if i >= len(lines):
            return False
        
        window = norm_text(" ".join(lines[i:i + self.HEADER_WINDOW_SIZE]))
        return all(token in window for token in self.HEADERS)
    
    def _consume_header(self, lines: List[str], start_idx: int) -> int:
        """
        Override: Busca PRIMERA MÉTRICA CONOCIDA (simple).
        No busca secciones ni tokens header (solo hay métricas).
        """
        i = start_idx
        limit = min(len(lines), start_idx + 40)
        
        while i < limit:
            ln = lines[i].strip()
            if ln in self.ROW_LABELS_SET:
                return i
            i += 1
        
        return i
    
    def _is_probable_new_block_start(self, lines: List[str], i: int) -> bool:
        """
        Detecta inicio de NUEVA TABLA (nuevo segmento).
        Usado para separar "Consolidado" | "CM Perú" | "Neg. Internacionales".
        """
        ln = lines[i].strip()
        
        if not ln:
            return False
        
        # Si siguiente línea es header, es nueva tabla
        if i + 1 < len(lines) and self._looks_like_header(lines, i + 1):
            return True
        
        # Si línea larga sin números, probablemente es nuevo título
        return len(ln.split()) >= 8 and not is_numericish(ln)
    
    def extract(self, page_record: dict) -> List[Dict]:
        """
        Override: Detecta MÚLTIPLES TABLAS en la página.
        Cada tabla tiene headers → métricas → valores.
        """
        if (page_record.get("doc_type") or "").lower() != self.DOC_TYPE:
            return []
        
        text = (page_record.get("page_text") or "").strip()
        if not text:
            return []
        
        lines = normalize_lines(text)
        tables = []
        i = 0
        
        while i < len(lines):
            # Buscar header de tabla
            if not self._looks_like_header(lines, i):
                i += 1
                continue
            
            table_start = i
            unit = self._extract_unit(lines, i)
            title = self._extract_title(lines, i)
            cursor = self._consume_header(lines, i)
            
            rows = []
            
            while cursor < len(lines):
                ln = lines[cursor].strip()
                
                if not ln:
                    cursor += 1
                    continue
                
                # Detectar fin de tabla
                if self._looks_like_header(lines, cursor):
                    break
                
                if self._is_probable_new_block_start(lines, cursor):
                    break
                
                # Detectar métrica
                if ln not in self.ROW_LABELS_SET:
                    cursor += 1
                    continue
                
                metric = ln
                cursor += 1
                
                # Leer 10 valores (T1-T4 + Año de 2 años)
                values, cursor = self._read_values(lines, cursor)
                if not values:
                    continue
                
                # Formatear row
                row = self._format_row(metric, self._pad_values(values))
                rows.append(row)
            
            # Guardar tabla
            if rows:
                table_end = cursor
                if table_end > table_start:
                    page_record.setdefault("table_ranges", []).append((table_start, table_end))
                
                table = self._format_table(title, unit, rows)
                tables.append(table)
            
            i = cursor if cursor > i else i + 1
        
        return tables
    
    # ========== FORMATO ESPECÍFICO ==========
    
    def _extract_unit(self, lines: List[str], i: int) -> str:
        """Override: busca "millones de soles"."""
        for j in range(max(0, i - 6), min(len(lines), i + 12)):
            low = lines[j].lower()
            if "millones de soles" in low:
                return "millones de soles"
        return "unidad no identificada"
    
    def _extract_title(self, lines: List[str], start_idx: int) -> str:
        """Override: filtra patterns específicos."""
        candidates = []
        for j in range(max(0, start_idx - 6), start_idx):
            ln = lines[j].strip()
            if not ln:
                continue
            low = ln.lower()
            
            # Filtros
            if "millones de soles" in low:
                continue
            if ln in {"2023", "2024", "T1", "T2", "T3", "T4", "Año"}:
                continue
            
            candidates.append(ln)
        
        return candidates[-1] if candidates else self.DEFAULT_TITLE
    
    def _format_row(self, metric: str, values: List[str]) -> Dict:
        """
        Mapea 10 valores a columnas específicas.
        Orden: T1-T4 + Año de 2023, luego T1-T4 + Año de 2024.
        """
        (
            y2023_t1,
            y2023_t2,
            y2023_t3,
            y2023_t4,
            y2023_y,
            y2024_t1,
            y2024_t2,
            y2024_t3,
            y2024_t4,
            y2024_y,
        ) = values
        
        return {
            "metric": metric,
            "2023_t1": y2023_t1,
            "2023_t2": y2023_t2,
            "2023_t3": y2023_t3,
            "2023_t4": y2023_t4,
            "2023_year": y2023_y,
            "2024_t1": y2024_t1,
            "2024_t2": y2024_t2,
            "2024_t3": y2024_t3,
            "2024_t4": y2024_t4,
            "2024_year": y2024_y,
        }
    
    def _format_table(self, title: str, unit: str, rows: List[Dict]) -> Dict:
        """Formato específico para indicadores trimestrales."""
        reconstructed = [
            f"TABLA INDICADORES TRIMESTRALES | Título: {title} | Unidad: {unit}"
        ]
        
        for r in rows:
            reconstructed.append(
                f"{r['metric']} | "
                f"2023: T1 {r['2023_t1']} | T2 {r['2023_t2']} | T3 {r['2023_t3']} | T4 {r['2023_t4']} | Año {r['2023_year']} | "
                f"2024: T1 {r['2024_t1']} | T2 {r['2024_t2']} | T3 {r['2024_t3']} | T4 {r['2024_t4']} | Año {r['2024_year']}"
            )
        
        return {
            "table_type": self.TABLE_TYPE,
            "title": title,
            "unit": unit,
            "rows": rows,
            "reconstructed_text": "\n".join(reconstructed),
        }


def extract_earnings_report_tables_family_6(page_record: dict) -> List[Dict]:
    """Punto de entrada."""
    extractor = EarningsFamily6()
    return extractor.extract(page_record)