# Design note:
# Metadata inference is handled within loader.py to keep the ingestion
# pipeline simple. The loader is the single source of truth for
# document/page metadata.
# =============================================================================l
# Loader de documentos (PDF -> páginas).                                       |  
#                                                                              |  
# Responsabilidad:                                                             |  
# - Leer PDFs desde data/raw y extraer texto por página.                       |
# - Adjuntar metadata base por documento y página (ej. año, tipo de documento, |
#   auditado/no auditado, fuente, página).                                     |  
# - Entregar una salida trazable (page-level) para habilitar citas precisas.   |
#                                                                              |  
# No hace:                                                                     |
# - No limpia agresivamente el texto (eso es del cleaner).                     |
# - No crea chunks (eso es del splitter).                                      |
# - No genera embeddings ni escribe al vector store (eso es del build_index).  |
# =============================================================================|
from pathlib import Path
import re
import fitz
from typing import Iterator


NO_AUDITED_TOKENS = ["noauditado", "no_auditado", "no-auditado"]
MONTHS_ES = {
    "enero": "01",
    "febrero": "02",
    "marzo": "03",
    "abril": "04",
    "mayo": "05",
    "junio": "06",
    "julio": "07",
    "agosto": "08",
    "septiembre": "09",
    "setiembre": "09",
    "octubre": "10",
    "noviembre": "11",
    "diciembre": "12",
}

def get_pdfs_paths(directory: Path) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"El directorio {directory} no existe.")

    return sorted(directory.rglob("*.pdf"), key=lambda p: str(p.relative_to(directory)))

def extract_metadata(pdf_path: Path) -> dict:
    name_doc = pdf_path.stem
    name_lower = name_doc.lower() # convencion. No es para metadata
    source_path = pdf_path.as_posix()
    year = re.search(r"(20\d{2})", name_lower)
    year = int(year.group(1)) if year else None
    doc_type = pdf_path.parent.name.lower()
    
    if any(token in name_lower for token in NO_AUDITED_TOKENS):
        audited = False
    elif "auditado" in name_lower:
        audited = True
    else:
        audited = False
    
    period = None
    
    for month, mm in MONTHS_ES.items():
        if month in name_lower:
            period = mm
            break
    
    if period is not None and year:
        period = f"{year}-{period}"
    else:
        period = "no_definido"

    source = "Alicorp"
    
    return {
        "doc_id": name_doc,
        "source_path": source_path,
        "year": year,
        "doc_type": doc_type,
        "audited": audited,
        "period": period,
        "source": source
    }
    
def extract_pages_text(pdf_path: Path) -> Iterator[dict]:
    with fitz.open(pdf_path) as doc:
        for i in range(doc.page_count):
            text = doc.load_page(i).get_text("text").strip()
            
            yield {
                "page_number": i + 1,
                "page_text": text
            }

def full_extract_document(pdf_path: Path) -> Iterator[dict]:
    metadata = extract_metadata(pdf_path)
    for page in extract_pages_text(pdf_path):
        yield {
            **metadata,
            **page
        }
    
