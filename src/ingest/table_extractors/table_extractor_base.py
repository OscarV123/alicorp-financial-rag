"""
Clase base para extractores de tablas financieras.

Asume estructura de tabla:
  ENCABEZADO → MÉTRICA + VALORES → MÉTRICA + VALORES → ...

Cada familia (family_1.py, family_2.py, etc) hereda esto
y solo define:
  - Headers esperados
  - Row labels conocidas
  - Tamaños de ventana
  - Formato de output
"""
from typing import Dict, List, Optional, Set, Tuple
from src.ingest.table_extractors.common import normalize_lines, is_numericish, norm_text


class SimpleTableExtractor:
    """
    Extractor genérico de tablas financieras.
    
    CONFIGURABLE: cada subclase define su estructura
    GENÉRICO: lógica de extracción es idéntica para todas
    """
    
    # ========== CONFIGURACIÓN (cada familia la sobrescribe) ==========
    TABLE_TYPE: int = 0
    DOC_TYPE: str = "earnings_reports"
    HEADERS: List[str] = []
    ROW_LABELS: List[str] = []
    HEADER_WINDOW_SIZE: int = 8
    MAX_VALUES: int = 6
    MAX_LINES: int = 1
    DEFAULT_TITLE: str = "Tabla"
    
    def __init__(self):
        """Inicializa sets para búsquedas O(1)."""
        self.ROW_LABELS_SET: Set[str] = set(sorted(self.ROW_LABELS, key=len, reverse=True))
        self.HEADERS_SET: Set[str] = set(self.HEADERS)
    
    # ========== MÉTODOS GENÉRICOS (no tocar) ==========
    
    def _looks_like_header(self, lines: List[str], i: int) -> bool:
        """Detecta si línea(s) parecen un encabezado."""
        if self.HEADER_WINDOW_SIZE == 1:
            window = lines[i].strip() if i < len(lines) else ""
        else:
            window = " | ".join(lines[i:i + self.HEADER_WINDOW_SIZE])
        
        return all(x in window for x in self.HEADERS)
    
    def _extract_unit(self, lines: List[str], i: int) -> str:
        """Extrae unidad de medida (genérico)."""
        for j in range(max(0, i - 3), min(len(lines), i + 2)):
            low = lines[j].lower()
            if "en millones de soles" in low:
                return "millones de soles"
            if "en millones de dólares" in low or "en millones de dolares" in low:
                return "millones de dólares"
            if "en miles de soles" in low:
                return "miles de soles"
        return "unidad no identificada"
    
    def _extract_title(self, lines: List[str], start_idx: int) -> str:
        """Extrae título de la tabla (genérico)."""
        candidates = []
        for j in range(max(0, start_idx - 8), start_idx):
            ln = lines[j].strip()
            if not ln:
                continue
            low = ln.lower()
            
            # Filtros genéricos
            if any(p in low for p in ["en millones", "en miles", "por los periodos"]):
                continue
            if ln in self.HEADERS or ln in self.ROW_LABELS:
                continue
            
            candidates.append(ln)
        
        return candidates[-1] if candidates else self.DEFAULT_TITLE
    
    def _consume_header(self, lines: List[str], start_idx: int) -> int:
        """Salta encabezado, retorna inicio de contenido."""
        i = start_idx
        
        if i < len(lines) and lines[i].lower().startswith("en millones"):
            i += 1
        
        while i < len(lines) and lines[i].strip() in self.HEADERS:
            i += 1
        
        return i
    
    def _match_label_at(self, lines: List[str], i: int) -> Optional[Tuple[str, int]]:
        """Detecta label (puede ser multi-línea)."""
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
            
            if candidate in self.ROW_LABELS_SET:
                return candidate, i + span
        
        return None
    
    def _read_values(self, lines: List[str], i: int) -> Tuple[List[str], int]:
        """Lee valores numéricos de una fila."""
        values = []
        while i < len(lines) and len(values) < self.MAX_VALUES:
            ln = lines[i].strip()
            
            if not ln:
                i += 1
                continue
            
            if self._looks_like_header(lines, i):
                break
            if self._match_label_at(lines, i) is not None:
                break
            if not is_numericish(ln):
                break
            
            values.append(ln)
            i += 1
        
        return values, i
    
    def _pad_values(self, values: List[str]) -> List[str]:
        """Rellena valores faltantes."""
        vals = values[:]
        while len(vals) < self.MAX_VALUES:
            vals.append("-")
        return vals[:self.MAX_VALUES]
    
    # ========== MÉTODOS ABSTRACTOS (cada familia implementa) ==========
    
    def _format_row(self, metric: str, values: List[str]) -> Dict:
        """Mapea valores a estructura de row. IMPLEMENTAR EN SUBCLASE."""
        raise NotImplementedError("Cada familia debe implementar _format_row()")
    
    def _format_table(self, title: str, unit: str, rows: List[Dict]) -> Dict:
        """Formatea tabla final. IMPLEMENTAR EN SUBCLASE."""
        raise NotImplementedError("Cada familia debe implementar _format_table()")
    
    # ========== LÓGICA PRINCIPAL (genérica) ==========
    
    def extract(self, page_record: dict) -> List[Dict]:
        """Extrae todas las tablas del documento."""
        if (page_record.get("doc_type") or "").lower() != self.DOC_TYPE:
            return []
        
        text = (page_record.get("page_text") or "").strip()
        if not text:
            return []
        
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
                if not metric_match:
                    if len(ln.split()) >= 4 and not is_numericish(ln):
                        break
                    cursor += 1
                    continue
                
                metric, cursor = metric_match
                
                values, cursor = self._read_values(lines, cursor)
                if not values:
                    continue
                
                row = self._format_row(metric, self._pad_values(values))
                rows.append(row)
            
            if rows:
                table_end = cursor
                if table_end > table_start:
                    page_record.setdefault("table_ranges", []).append((table_start, table_end))
                
                table = self._format_table(title, unit, rows)
                tables.append(table)
            
            i = cursor if cursor > i else i + 1
        
        return tables