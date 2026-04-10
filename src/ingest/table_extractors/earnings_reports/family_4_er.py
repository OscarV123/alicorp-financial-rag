"""
Estado de Situación Financiera - Familia 4 (Financial Position)
Tabla BALANCEADA (Activos izquierda | Pasivos+Patrimonio derecha).
Más compleja que Income Statement.
"""
from typing import Dict, List, Optional, Tuple, Set
from src.ingest.table_extractors.common import normalize_lines, is_numericish, norm_text
from src.ingest.table_extractors.table_extractor_base import SimpleTableExtractor


class EarningsFamily4(SimpleTableExtractor):
    """Extrae tablas de ESTADO DE SITUACIÓN FINANCIERA (familia 4)."""
    
    # ========== CONFIGURACIÓN ==========
    TABLE_TYPE = 4
    DOC_TYPE = "earnings_reports"  # En realidad es financial_statements, pero adaptamos
    
    HEADERS = [
        "notas",
        "al 31 de diciembre 2024",
        "al 31 de diciembre 2023",
    ]
    
    # LADO IZQUIERDO (ACTIVOS)
    LEFT_SECTION_LABELS = {
        "Activos",
        "Activos Corrientes",
        "Activos No Corrientes",
    }
    
    LEFT_ROW_LABELS = [
        "Efectivo y Equivalentes al Efectivo",
        "Otros Activos Financieros",
        "Cuentas por Cobrar Comerciales",
        "Cuentas por Cobrar a Entidades Relacionadas",
        "Otras Cuentas por Cobrar",
        "Anticipos",
        "Inventarios",
        "Activos por Impuestos a las Ganancias",
        "Otros Activos no Financieros",
        "Disponible para venta",
        "Total Activos Corrientes",
        "Inversiones",
        "Propiedades de Inversión",
        "Propiedades, Planta y Equipo",
        "Activos Intangibles",
        "Activos por Impuestos Diferidos",
        "Activos por Impuestos Corrientes, no Corrientes",
        "Plusvalía",
        "Total Activos No Corrientes",
        "Total Activos",
    ]
    
    # LADO DERECHO (PASIVOS + PATRIMONIO)
    RIGHT_SECTION_LABELS = {
        "Pasivos",
        "Pasivos Corrientes",
        "Pasivos No Corrientes",
        "Patrimonio",
    }
    
    RIGHT_ROW_LABELS = [
        "Otros Pasivos Financieros",
        "Cuentas por Pagar Comerciales",
        "Cuentas por Pagar a Entidades Relacionadas",
        "Otras Cuentas por Pagar",
        "Ingresos Diferidos",
        "Provisión por Beneficios a los Empleados",
        "Provisiones",
        "Pasivos por Impuestos a las Ganancias",
        "Otros Pasivos No Financieros",
        "Total Pasivos Corrientes",
        "Pasivos por Impuestos Diferidos",
        "Pasivos por Impuestos Corrientes, no Corrientes",
        "Total Pasivos No Corrientes",
        "Total Pasivos",
        "Capital Emitido",
        "Acciones de Inversión",
        "Acciones Propias en Cartera",
        "Reservas",
        "Resultados Acumulados",
        "Otras Reservas de Patrimonio",
        "Patrimonio Atribuible a los Propietarios de la Controladora",
        "Participaciones no Controladoras",
        "Total Patrimonio",
        "Total pasivos y patrimonio",
    ]
    
    HEADER_WINDOW_SIZE = 50
    MAX_VALUES = 3  # Nota + 2024 + 2023 (pero puede ser menos)
    MAX_LINES = 4
    DEFAULT_TITLE = "Estado de situación financiera consolidado"
    
    def __init__(self):
        """Inicializa sets para ambos lados."""
        super().__init__()
        # Crear sets separados para left y right
        self.LEFT_ROW_LABELS_SET = set(sorted(self.LEFT_ROW_LABELS, key=len, reverse=True))
        self.RIGHT_ROW_LABELS_SET = set(sorted(self.RIGHT_ROW_LABELS, key=len, reverse=True))
        self.LEFT_SECTION_LABELS_SET = set(self.LEFT_SECTION_LABELS)
        self.RIGHT_SECTION_LABELS_SET = set(self.RIGHT_SECTION_LABELS)
        self.ALL_SECTION_LABELS_SET = self.LEFT_SECTION_LABELS_SET.union(self.RIGHT_SECTION_LABELS_SET)
    
    # ========== OVERRIDES ESPECÍFICOS ==========
    
    def _looks_like_header(self, lines: List[str], i: int) -> bool:
        """
        Override: Headers cortados en ventana grande.
        Esta tabla tiene headers en múltiples líneas en ambos lados.
        """
        if i >= len(lines):
            return False
        
        window = norm_text(" ".join(lines[i:i + self.HEADER_WINDOW_SIZE])).lower()
        return all(token in window for token in self.HEADERS)
    
    def _consume_header(self, lines: List[str], start_idx: int) -> int:
        """
        Override: Busca PRIMERA SECCIÓN O MÉTRICA, no tokens.
        Los headers están cortados y no aparecen como strings exactos.
        """
        i = start_idx
        limit = min(len(lines), start_idx + 80)
        
        while i < limit:
            # Busca sección (ej: "Activos", "Pasivos Corrientes")
            if self._match_section_at(lines, i):
                return i
            # Busca métrica izquierda o derecha
            if self._match_label_at(lines, i, self.LEFT_ROW_LABELS_SET, max_lines=4):
                return i
            if self._match_label_at(lines, i, self.RIGHT_ROW_LABELS_SET, max_lines=4):
                return i
            i += 1
        
        return i
    
    def _match_section_at(self, lines: List[str], i: int) -> Optional[Tuple[str, int]]:
        """
        Detecta SECCIÓN (Activos, Pasivos, Patrimonio, etc).
        Las secciones pueden estar en 1-2 líneas.
        """
        parts = []
        for span in range(1, 3):  # Max 2 líneas para secciones
            if i + span - 1 >= len(lines):
                break
            
            piece = lines[i + span - 1].strip()
            if not piece:
                break
            
            parts.append(piece)
            candidate = norm_text(" ".join(parts))
            
            if candidate in self.ALL_SECTION_LABELS_SET:
                return candidate, i + span
        
        return None
    
    def _match_label_at(
        self,
        lines: List[str],
        i: int,
        labels_set: Set[str],
        max_lines: int = 4
    ) -> Optional[Tuple[str, int]]:
        """
        Override: Detecta métrica de un SET específico.
        Puede ser multi-línea (hasta 4 líneas).
        """
        if i >= len(lines):
            return None
        
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
        - [nota, val_2024, val_2023] si first token es corto número
        - [val_2024, val_2023] si no hay nota
        - [val_2024] si solo un valor
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
            if self._match_section_at(lines, i):
                break
            if self._match_label_at(lines, i, self.LEFT_ROW_LABELS_SET, max_lines=4):
                break
            if self._match_label_at(lines, i, self.RIGHT_ROW_LABELS_SET, max_lines=4):
                break
            
            if not is_numericish(ln):
                break
            
            tokens.append(ln)
            i += 1
        
        # Decidir qué es cada token
        note = "-"
        val_2024 = "-"
        val_2023 = "-"
        
        # Heurística: si primer token es número corto (<=3 chars), es nota
        if len(tokens) >= 3 and tokens[0].replace(",", "").isdigit() and len(tokens[0]) <= 3:
            note, val_2024, val_2023 = tokens[0], tokens[1], tokens[2]
        elif len(tokens) >= 2:
            val_2024, val_2023 = tokens[0], tokens[1]
        elif len(tokens) == 1:
            val_2024 = tokens[0]
        
        return note, val_2024, val_2023, i
    
    def extract(self, page_record: dict) -> List[Dict]:
        """
        Override: Lógica principal para tabla BALANCEADA.
        Procesa AMBOS lados (izquierda + derecha) simultáneamente.
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
            current_left_section = ""
            current_right_section = ""
            
            while cursor < len(lines):
                ln = lines[cursor].strip()
                
                if not ln:
                    cursor += 1
                    continue
                
                if self._looks_like_header(lines, cursor):
                    break
                
                # ============ DETECTAR SECCIÓN ============
                section_match = self._match_section_at(lines, cursor)
                if section_match:
                    section_text, cursor = section_match
                    
                    # Clasificar en LEFT o RIGHT
                    if section_text in self.LEFT_SECTION_LABELS_SET:
                        current_left_section = section_text
                    if section_text in self.RIGHT_SECTION_LABELS_SET:
                        current_right_section = section_text
                    
                    continue
                
                # ============ DETECTAR MÉTRICA LEFT (ACTIVOS) ============
                left_match = self._match_label_at(lines, cursor, self.LEFT_ROW_LABELS_SET, max_lines=4)
                if left_match:
                    metric, cursor = left_match
                    note, v2024, v2023, cursor = self._read_note_and_values(lines, cursor)
                    
                    rows.append({
                        "side": "activos",
                        "section": current_left_section,
                        "metric": metric,
                        "note": note,
                        "value_2024": v2024,
                        "value_2023": v2023,
                    })
                    continue
                
                # ============ DETECTAR MÉTRICA RIGHT (PASIVOS + PATRIMONIO) ============
                right_match = self._match_label_at(lines, cursor, self.RIGHT_ROW_LABELS_SET, max_lines=4)
                if right_match:
                    metric, cursor = right_match
                    note, v2024, v2023, cursor = self._read_note_and_values(lines, cursor)
                    
                    rows.append({
                        "side": "pasivos_patrimonio",
                        "section": current_right_section,
                        "metric": metric,
                        "note": note,
                        "value_2024": v2024,
                        "value_2023": v2023,
                    })
                    continue
                
                # Corte defensivo
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
        """Override: busca "miles de soles" (no "millones")."""
        for j in range(max(0, i - 6), min(len(lines), i + 8)):
            low = lines[j].lower()
            if "en miles de soles" in low:
                return "miles de soles"
        return "unidad no identificada"
    
    def _extract_title(self, lines: List[str], start_idx: int) -> str:
        """Override: filtra más casos específicos."""
        candidates = []
        for j in range(max(0, start_idx - 8), start_idx):
            ln = lines[j].strip()
            if not ln:
                continue
            low = ln.lower()
            
            # Filtros específicos de esta tabla
            if low.startswith("al cierre de"):
                continue
            if "miles de soles" in low:
                continue
            if low == "notas":
                continue
            
            candidates.append(ln)
        
        return candidates[-1] if candidates else self.DEFAULT_TITLE
    
    def _format_row(self, metric: str, values: List[str]) -> Dict:
        """No se usa en esta familia (usa formato custom en _format_table)."""
        raise NotImplementedError("Family4 usa formato custom")
    
    def _format_table(self, title: str, unit: str, rows: List[Dict]) -> Dict:
        """Formato específico para tabla balanceada."""
        reconstructed = [
            f"TABLA ESTADO SITUACION FINANCIERA CONSOLIDADO | Título: {title} | Unidad: {unit}"
        ]
        
        for r in rows:
            reconstructed.append(
                f"[{r['side']}] {r['section']} | {r['metric']} | Nota: {r['note']} | "
                f"2024: {r['value_2024']} | 2023: {r['value_2023']}"
            )
        
        return {
            "table_type": self.TABLE_TYPE,
            "title": title,
            "unit": unit,
            "rows": rows,
            "reconstructed_text": "\n".join(reconstructed),
        }


def extract_earnings_report_tables_family_4(page_record: dict) -> List[Dict]:
    """Punto de entrada."""
    extractor = EarningsFamily4()
    return extractor.extract(page_record)