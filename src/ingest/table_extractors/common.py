"""
Utilidades generales para procesamiento de OCR y tablas.
Sin opinión sobre estructura específica de datos.
"""
import re
from typing import List, Tuple, Optional

# ============================================================================
# REGEX PATTERNS - Compiladas una sola vez
# ============================================================================
_NON_PRINTING = re.compile(r'[\ufeff\u200b\u200c\u200d]+')
_SPACE_RE = re.compile(r'[ \t]+')
_YEAR_RE = re.compile(r"^20\d{2}$")
_NOTE_RE = re.compile(r"^\d+\s*(?:\([A-Za-z]+\))*$")

# ============================================================================
# LIMPIEZA Y NORMALIZACIÓN DE TEXTO
# ============================================================================

def normalize_lines(text: str) -> List[str]:
    """
    Normaliza texto OCR en líneas limpias.
    
    - Estandariza saltos de línea
    - Elimina caracteres invisibles
    - Normaliza espacios
    - Retorna lista de líneas limpias
    """
    if not text:
        return []

    normalized = []
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = _NON_PRINTING.sub('', text)
    text = text.replace('\xa0', ' ')
    text = text.replace('\f', '\n')

    for line in text.split('\n'):
        cleaned = _SPACE_RE.sub(' ', line).strip()
        normalized.append(cleaned)

    return normalized


def norm_text(s: str) -> str:
    """Normaliza espacios múltiples a uno solo."""
    return " ".join(s.split()).strip()


def is_numericish(value: str) -> bool:
    """
    Valida si un string se parece a un número.
    
    Tolerante con:
    - Números negativos: "-100", "(100)"
    - Porcentajes: "100%"
    - Moneda: "S/ 100"
    - Decimales: "100.5"
    - Punto y coma: "1,000.5"
    - Símbolos especiales: "100x", "100p.p."
    
    Rechaza:
    - Strings vacíos
    - Texto mixto (solo "100abc" NO, pero "100%" SÍ)
    - Múltiples decimales: "1.0.5" NO
    """
    if not value:
        return False

    v = value.strip()
    if v in {'-', '—', '–'}:
        return True

    v = v.strip('()')
    v = re.sub(r'^[sS]/\s*', '', v)
    v = v.replace('%', '')
    v = v.replace('p.p.', '').replace('pp', '')
    v = v.replace('x', '')
    v = v.replace(' ', '').replace(',', '')

    if not v:
        return False

    if v[0] in '+-':
        v = v[1:]

    parts = v.split('.')
    if len(parts) > 2:
        return False
    
    return all(part.isdigit() for part in parts if part)


# ============================================================================
# UTILIDADES DE BÚSQUEDA Y VALIDACIÓN
# ============================================================================

def is_valid_year(token: str) -> bool:
    """Verifica si es un año válido (formato 20XX)."""
    return bool(_YEAR_RE.match(token))


def is_note_token(token: str) -> bool:
    """Verifica si es una nota (ej: '1', '2(a)', etc)."""
    token = norm_text(token)
    return bool(_NOTE_RE.match(token))


def extract_years(
    lines: List[str],
    i: int,
    max_lines: int = 90
) -> Optional[Tuple[str, str]]:
    """
    Extrae dos años diferentes de una ventana de líneas.
    
    Busca formato 20XX (ej: 2023, 2024).
    Retorna primer año encontrado y segundo año encontrado.
    """
    years = []
    for ln in lines[i:i + max_lines]:
        token = norm_text(ln)
        if is_valid_year(token) and token not in years:
            years.append(token)
    
    return (years[0], years[1]) if len(years) >= 2 else None


# ============================================================================
# UTILIDADES DE MANIPULACIÓN DE LISTAS
# ============================================================================

def pad_values(values: List[str], n: int, pad_char: str = "-") -> List[str]:
    """
    Rellena una lista de valores hasta longitud n.
    
    Args:
        values: lista original
        n: longitud deseada
        pad_char: carácter de relleno (por defecto "-")
    
    Returns:
        Lista con exactamente n elementos
    """
    vals = values[:]
    while len(vals) < n:
        vals.append(pad_char)
    return vals[:n]


# ============================================================================
# UTILIDADES DE POSICIÓN DE TABLA
# ============================================================================

def remove_table_lines(page_record: dict) -> str:
    """
    Elimina líneas que pertenecen a tablas extraídas.
    
    Usa los rangos guardados en page_record["table_ranges"].
    Retorna el page_text con esas líneas eliminadas.
    
    Útil para: después de extraer tablas, limpiar page_text
    para procesamiento de NLP/embeddings.
    """
    text = page_record.get("page_text", "") or ""
    if not text:
        return ""

    lines = normalize_lines(text)
    ranges = sorted(page_record.get("table_ranges", []))
    merged = []
    
    # Fusionar rangos que se solapan
    for start, end in ranges:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    # Marcar líneas que pertenecen a tablas
    mask = [False] * len(lines)
    for start, end in merged:
        for idx in range(start, min(end, len(lines))):
            mask[idx] = True

    # Mantener solo líneas NO marcadas
    kept = [line for idx, line in enumerate(lines) if idx < len(mask) and not mask[idx]]
    return "\n".join(kept)