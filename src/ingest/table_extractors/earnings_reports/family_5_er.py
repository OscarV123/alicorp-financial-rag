"""
Estado de Flujo de Efectivo - Familia 5 (Cash Flow)
Estructura lineal con SECCIONES y SUB-SECCIONES anidadas.
Similar complejidad a Family4 pero estructura diferente.
"""
from typing import Dict, List, Optional, Tuple 
from src.ingest.table_extractors.common import normalize_lines, is_numericish, norm_text
from src.ingest.table_extractors.table_extractor_base import SimpleTableExtractor


class EarningsFamily5(SimpleTableExtractor):
    """Extrae tablas de ESTADO DE FLUJO DE EFECTIVO (familia 5)."""
    
    # ========== CONFIGURACIÓN ==========
    TABLE_TYPE = 5
    DOC_TYPE = "earnings_reports"  # En realidad es financial_statements
    
    HEADERS = [
        "notas",
        "del 1 de enero de 2024 al 31 de diciembre de 2024",
        "del 1 de enero de 2023 al 31 de diciembre de 2023",
    ]
    
    # SECCIONES PRINCIPALES
    SECTION_ROWS = [
        "FLUJO DE EFECTIVO DE ACTIVIDADES DE OPERACIÓN",
        "FLUJO DE EFECTIVO DE ACTIVIDADES DE INVERSIÓN",
        "FLUJO DE EFECTIVO DE ACTIVIDADES DE FINANCIACIÓN",
    ]
    
    # SUB-SECCIONES (dentro de cada sección)
    SUBSECTION_ROWS = [
        "Cobros provenientes de (debido a):",
        "Pagos a (debido a):",
    ]
    
    # TODAS LAS MÉTRICAS
    ROW_LABELS = [
        "Venta de Bienes y Prestación de Servicios",
        "Otros Cobros de Efectivo",
        "Proveedores de Bienes y Servicios",
        "Salarios",
        "Impuestos a las Ganancias (Pagados)",
        "Otros Pagos de Efectivo",
        "Otros Cobros (Pagos) de Efectivo",
        "Flujos de Efectivo de Actividades de Operación",
        "Venta de Propiedades, Planta y Equipo",
        "Venta de Participaciones en Negocios Conjuntos, Neto del Efectivo Desapropiado",
        "Intereses Recibidos",
        "Venta de Activos Intangibles",
        "Compra de Subsidiarias, Neto del Efectivo Adquirido",
        "Compra de Propiedades, Planta y Equipo",
        "Compra de Activos Intangibles",
        "Impuesto a la Renta",
        "Flujos de Efectivo de Actividades de Inversión",
        "Obtención de Préstamos",
        "Amortización o Pago de Préstamos",
        "Arrendamiento Financiero",
        "Recompra de acciones",
        "Dividendos Pagados",
        "Intereses Pagados",
        "Flujos de Efectivo de Actividades de Financiación",
        "Aumento (Disminución) Neto de Efectivo, Antes de las Variaciones en las Tasas de Cambio",
        "Efectos de las Variaciones en las Tasas de Cambio sobre el Efectivo",
        "Aumento (Disminución) Neto de Efectivo",
        "Efectivo y Equivalente al Efectivo al Inicio del Ejercicio",
        "Efectivo y Equivalente al Efectivo al Finalizar el Ejercicio",
    ]
    
    HEADER_WINDOW_SIZE = 40
    MAX_VALUES = 3  # Nota + 2024 + 2023
    MAX_LINES = 4
    DEFAULT_TITLE = "Estado de flujo de efectivo consolidado"
    
    def __init__(self):
        """Inicializa sets para secciones, sub-secciones y métricas."""
        super().__init__()
        self.SECTION_ROWS_SET = set(self.SECTION_ROWS)
        self.SUBSECTION_ROWS_SET = set(self.SUBSECTION_ROWS)
        self.ROW_LABELS_SET = set(sorted(self.ROW_LABELS, key=len, reverse=True))
        # Union de todo para detección rápida
        self.ALL_CONTROL_ROWS_SET = self.SECTION_ROWS_SET.union(
            self.SUBSECTION_ROWS_SET
        ).union(self.ROW_LABELS_SET)
    
    # ========== OVERRIDES ESPECÍFICOS ==========
    
    def _looks_like_header(self, lines: List[str], i: int) -> bool:
        """
        Override: Headers cortados en ventana grande.
        Esta tabla tiene headers largos en múltiples líneas.
        """
        if i >= len(lines):
            return False
        
        window = norm_text(" ".join(lines[i:i + self.HEADER_WINDOW_SIZE])).lower()
        return all(token in window for token in self.HEADERS)
    
    def _consume_header(self, lines: List[str], start_idx: int) -> int:
        """
        Override: Busca PRIMERA SECCIÓN (no tokens header).
        Los headers están cortados, así que busca primer control row.
        """
        i = start_idx
        limit = min(len(lines), start_idx + 80)
        
        while i < limit:
            # Busca sección
            if self._match_row_at(lines, i, self.SECTION_ROWS, max_lines=2):
                return i
            # Busca métrica
            if self._match_row_at(lines, i, self.ROW_LABELS, max_lines=4):
                return i
            i += 1
        
        return i
    
    def _match_row_at(
        self,
        lines: List[str],
        i: int,
        labels: List[str],
        max_lines: int = 4
    ) -> Optional[Tuple[str, int]]:
        """
        Detecta FILA (sección, sub-sección o métrica).
        Puede ser multi-línea.
        """
        if i >= len(lines):
            return None
        
        labels_set = set(labels)  # Convertir a set para búsqueda O(1)
        parts = []
        
        for span in range(1, max_lines + 1):
            if i + span - 1 >= len(lines):
                break
            
            piece = lines[i + span - 1].strip()
            if not piece:
                break
            
            parts.append(piece)
            candidate = norm_text(" ".join(parts))
            
            if candidate in labels_set:
                return candidate, i + span
        
        return None
    
    def _read_note_and_values(self, lines: List[str], i: int) -> Tuple[str, str, str, int]:
        """
        Override: Lee nota (opcional) + 2 valores (2024, 2023).
        
        Casos:
        - [nota, val_2024, val_2023] si primer token es número puro
        - [val_2024, val_2023] si no hay nota
        - [val_2024] si solo un valor
        
        Stop conditions: header, sección, sub-sección, métrica
        """
        tokens: List[str] = []
        
        while i < len(lines) and len(tokens) < 3:
            ln = lines[i].strip()
            
            if not ln:
                i += 1
                continue
            
            # Stop conditions
            if self._looks_like_header(lines, i):
                break
            if self._match_row_at(lines, i, self.SECTION_ROWS, max_lines=2):
                break
            if self._match_row_at(lines, i, self.SUBSECTION_ROWS, max_lines=2):
                break
            if self._match_row_at(lines, i, self.ROW_LABELS, max_lines=4):
                break
            
            if not is_numericish(ln):
                break
            
            tokens.append(ln)
            i += 1
        
        # Decidir qué es cada token
        note = "-"
        value_2024 = "-"
        value_2023 = "-"
        
        # Heurística: si primer token es número puro (después de limpiar comas),
        # probablemente es nota
        first_clean = tokens[0].replace(",", "") if tokens else ""
        
        if len(tokens) >= 3 and first_clean.isdigit() and len(first_clean) <= 3:
            # Caso: [nota, 2024, 2023]
            note, value_2024, value_2023 = tokens[0], tokens[1], tokens[2]
        elif len(tokens) >= 2:
            # Caso: [2024, 2023]
            value_2024, value_2023 = tokens[0], tokens[1]
        elif len(tokens) == 1:
            # Caso: [2024]
            value_2024 = tokens[0]
        
        return note, value_2024, value_2023, i
    
    def extract(self, page_record: dict) -> List[Dict]:
        """
        Override: Lógica principal con SECCIONES y SUB-SECCIONES.
        Estructura lineal (no balanceada como Family4).
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
            if not self._looks_like_header(lines, i):
                i += 1
                continue
            
            table_start = i
            unit = self._extract_unit(lines, i)
            title = self._extract_title(lines, i)
            cursor = self._consume_header(lines, i)
            
            rows = []
            current_section = ""
            current_subsection = ""
            
            while cursor < len(lines):
                ln = lines[cursor].strip()
                
                if not ln:
                    cursor += 1
                    continue
                
                if self._looks_like_header(lines, cursor):
                    break
                
                # ============ DETECTAR SECCIÓN ============
                section_match = self._match_row_at(lines, cursor, self.SECTION_ROWS, max_lines=2)
                if section_match:
                    current_section, cursor = section_match
                    current_subsection = ""  # Reset subsección cuando cambia sección
                    continue
                
                # ============ DETECTAR SUB-SECCIÓN ============
                subsection_match = self._match_row_at(lines, cursor, self.SUBSECTION_ROWS, max_lines=2)
                if subsection_match:
                    current_subsection, cursor = subsection_match
                    continue
                
                # ============ DETECTAR MÉTRICA ============
                metric_match = self._match_row_at(lines, cursor, self.ROW_LABELS, max_lines=4)
                if metric_match:
                    metric, cursor = metric_match
                    note, v2024, v2023, cursor = self._read_note_and_values(lines, cursor)
                    
                    rows.append({
                        "section": current_section,
                        "subsection": current_subsection,
                        "metric": metric,
                        "note": note,
                        "value_2024": v2024,
                        "value_2023": v2023,
                    })
                    continue
                
                # Corte defensivo: si ve texto largo, probablemente es fin de tabla
                if len(ln.split()) >= 8 and not is_numericish(ln):
                    break
                
                cursor += 1
            
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
        """Override: busca "miles de soles"."""
        for j in range(max(0, i - 8), min(len(lines), i + 8)):
            low = lines[j].lower()
            if "en miles de soles" in low:
                return "miles de soles"
        return "unidad no identificada"
    
    def _extract_title(self, lines: List[str], start_idx: int) -> str:
        """Override: filtra patterns específicos."""
        candidates = []
        for j in range(max(0, start_idx - 8), start_idx):
            ln = lines[j].strip()
            if not ln:
                continue
            low = ln.lower()
            
            # Filtros
            if low.startswith("por los periodos terminados"):
                continue
            if "en miles de soles" in low:
                continue
            if low == "notas":
                continue
            
            candidates.append(ln)
        
        return candidates[-1] if candidates else self.DEFAULT_TITLE
    
    def _format_row(self, metric: str, values: List[str]) -> Dict:
        """No se usa (formato custom)."""
        raise NotImplementedError("Family5 usa formato custom")
    
    def _format_table(self, title: str, unit: str, rows: List[Dict]) -> Dict:
        """Formato específico para flujo de efectivo."""
        reconstructed = [
            f"TABLA FLUJO EFECTIVO CONSOLIDADO | Título: {title} | Unidad: {unit}"
        ]
        
        for r in rows:
            reconstructed.append(
                f"{r['section']} | {r['subsection']} | {r['metric']} | "
                f"Nota: {r['note']} | 2024: {r['value_2024']} | 2023: {r['value_2023']}"
            )
        
        return {
            "table_type": self.TABLE_TYPE,
            "title": title,
            "unit": unit,
            "rows": rows,
            "reconstructed_text": "\n".join(reconstructed),
        }


def extract_earnings_report_tables_family_5(page_record: dict) -> List[Dict]:
    """Punto de entrada."""
    extractor = EarningsFamily5()
    return extractor.extract(page_record)