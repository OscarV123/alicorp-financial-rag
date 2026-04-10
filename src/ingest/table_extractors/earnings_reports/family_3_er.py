"""
Income Statement - Familia 3
Parsea tablas con headers cortados en OCR y métricas multi-línea.
"""
from typing import Dict, List, Optional, Tuple
from src.ingest.table_extractors.common import norm_text, is_numericish
from src.ingest.table_extractors.table_extractor_base import SimpleTableExtractor


class EarningsFamily3(SimpleTableExtractor):
    """Extrae tablas de INCOME STATEMENT (familia 3)."""
    
    # ========== CONFIGURACIÓN ==========
    TABLE_TYPE = 3
    HEADERS = [
        "notes",
        "trimestre del 1 de octubre al 31 de diciembre de 2024",
        "trimestre del 1 de octubre al 31 de diciembre de 2023",
        "periodo del 1 de enero al 31 de diciembre de 2024",
        "periodo del 1 de enero al 31 de diciembre de 2023",
    ]
    ROW_LABELS = [
        "Ingresos de Actividades Ordinarias",
        "Costo de Ventas",
        "Ganancia (Pérdida) Bruta",
        "Gastos de Ventas y Distribución",
        "Gastos de Administración",
        "Otros Ingresos Operativos",
        "Otros Gastos Operativos",
        "Otras Ganancias (Pérdidas)",
        "Ganancia (Pérdida) Operativa",
        "Ingresos Financieros",
        "Gastos Financieros",
        "Diferencias de Cambio Neto",
        "Participación en los Resultados de Asociadas",
        "Ganancia (Pérdida) antes de Impuestos",
        "Ingreso (Gasto) por Impuesto",
        "Ganancia (Pérdida) Neta de Operaciones Continuadas",
        "Ganancia (Pérdida) de Operaciones Discontinuadas",
        "Ganancia (Pérdida) Neta del Ejercicio",
        "Básica por Acción Ordinaria en Operaciones Continuas",
        "Básica por Acción de Inversión en Operaciones Continuas",
        "Básica por Acción Ordinaria en Operaciones Discontinuadas",
        "Básica por Acción de Inversión en Operaciones Discontinuadas",
        "Total de Ganancias (Pérdida) Básica por Acción Ordinaria",
        "Total de Ganancias (Pérdida) Básica por Acción Inversión",
        "Diluida por Acción Ordinaria en Operaciones Continuas",
        "Diluida por Acción de Inversión en Operaciones Continuas",
        "Diluida por Acción Ordinaria en Operaciones Discontinuadas",
        "Diluida por Acción de Inversión en Operaciones Discontinuadas",
        "Total ganancias (Pérdida) Diluida por Acción Ordinaria",
        "Total de Ganancias (Pérdida) Diluida por Acción Inversión",
    ]
    SECTION_ROWS = [
        "Ganancias (Pérdida) Básica por Acción:",
        "Ganancias (Pérdida) Diluida por Acción:",
    ]
    HEADER_WINDOW_SIZE = 40
    MAX_VALUES = 5
    MAX_LINES = 3
    DEFAULT_TITLE = "Estado de resultados consolidado"
    
    def __init__(self):
        """Inicializa sets además de las secciones."""
        super().__init__()
        self.SECTION_ROWS_SET = set(self.SECTION_ROWS)
    
    # ========== OVERRIDES ESPECÍFICOS ==========
    
    def _looks_like_header(self, lines: List[str], i: int) -> bool:
        """
        Override: Headers cortados en múltiples líneas.
        Requiere ventana grande + normalización.
        """
        if i >= len(lines):
            return False
        
        window = norm_text(" ".join(lines[i:i + self.HEADER_WINDOW_SIZE])).lower()
        return all(token in window for token in self.HEADERS)
    
    def _consume_header(self, lines: List[str], start_idx: int) -> int:
        """
        Override: En lugar de buscar tokens exactos del header,
        busca la PRIMERA MÉTRICA CONOCIDA.
        
        Esto es crítico porque los headers están cortados en OCR
        y no aparecen como strings exactos en líneas individuales.
        """
        i = start_idx
        limit = min(len(lines), start_idx + 60)
        
        # Busca la primera línea que sea una métrica conocida
        while i < limit:
            # Usa _match_label_at para detectar métrica (puede ser multi-línea)
            if self._match_label_at(lines, i) is not None:
                return i
            i += 1
        
        return i
    
    def _match_label_at(self, lines: List[str], i: int) -> Optional[Tuple[str, int]]:
        """
        Override: Detecta métricas y secciones (multi-línea).
        Retorna (label, posición_siguiente) o None.
        """
        if i >= len(lines):
            return None
        
        parts = []
        for span in range(1, self.MAX_LINES + 1):
            if i + span - 1 >= len(lines):
                break
            
            piece = lines[i + span - 1].strip()
            if not piece:
                break
            
            parts.append(piece)
            candidate = norm_text(" ".join(parts))
            
            # Busca PRIMERO en secciones, luego en métricas
            if candidate in self.SECTION_ROWS_SET:
                return candidate, i + span
            if candidate in self.ROW_LABELS_SET:
                return candidate, i + span
        
        return None
    
    def extract(self, page_record: dict) -> List[Dict]:
        """
        Override: Lógica principal con manejo especial de secciones.
        """
        if (page_record.get("doc_type") or "").lower() != self.DOC_TYPE:
            return []
        
        text = (page_record.get("page_text") or "").strip()
        if not text:
            return []
        
        from src.ingest.table_extractors.common import normalize_lines
        lines = normalize_lines(text)
        tables = []
        i = 0
        
        while i < len(lines):
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
                
                if self._looks_like_header(lines, cursor):
                    break
                
                metric_match = self._match_label_at(lines, cursor)
                if metric_match is None:
                    # Corte defensivo: si ve texto largo, es fin de tabla
                    if len(ln.split()) >= 6 and not is_numericish(ln):
                        break
                    cursor += 1
                    continue
                
                metric, cursor = metric_match
                
                # SKIP secciones (ej: "Ganancias (Pérdida) Básica por Acción:")
                if metric in self.SECTION_ROWS_SET:
                    continue
                
                # Leer valores
                values, cursor = self._read_values(lines, cursor)
                if not values:
                    continue
                
                # Formatear row
                row = self._format_row(metric, self._pad_values(values))
                rows.append(row)
            
            # Guardar tabla si tiene datos
            if rows:
                table_end = cursor
                if table_end > table_start:
                    page_record.setdefault("table_ranges", []).append((table_start, table_end))
                
                table = self._format_table(title, unit, rows)
                tables.append(table)
            
            i = cursor if cursor > i else i + 1
        
        return tables
    
    # ========== FORMATO ESPECÍFICO ==========
    
    def _format_row(self, metric: str, values: List[str]) -> Dict:
        """Mapea 5 valores a columnas de family_3."""
        note, q4_2024, q4_2023, y_2024, y_2023 = values
        return {
            "metric": metric,
            "note": note,
            "q4_2024": q4_2024,
            "q4_2023": q4_2023,
            "y_2024": y_2024,
            "y_2023": y_2023,
        }
    
    def _format_table(self, title: str, unit: str, rows: List[Dict]) -> Dict:
        """Formato de tabla para family_3."""
        reconstructed = [
            f"TABLA ESTADO RESULTADOS CONSOLIDADO | Título: {title} | Unidad: {unit}"
        ]
        for r in rows:
            reconstructed.append(
                f"{r['metric']} | Nota: {r['note']} | "
                f"Trimestre 2024: {r['q4_2024']} | Trimestre 2023: {r['q4_2023']} | "
                f"Periodo 2024: {r['y_2024']} | Periodo 2023: {r['y_2023']}"
            )
        
        return {
            "table_type": self.TABLE_TYPE,
            "title": title,
            "unit": unit,
            "rows": rows,
            "reconstructed_text": "\n".join(reconstructed),
        }


def extract_earnings_report_tables_family_3(page_record: dict) -> List[Dict]:
    """Punto de entrada."""
    extractor = EarningsFamily3()
    return extractor.extract(page_record)