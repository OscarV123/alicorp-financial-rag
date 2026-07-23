# ==============================================================================l
# Configuración central del proyecto RAG-Alicorp.                               |
#                                                                               |
# Qué contiene:                                                                 |
# - Rutas base (data/raw, data/processed, vector_store).                        |
# - Parámetros de chunking (tamaño y solapamiento).                             |
# - Parámetros de retrieval (top-k, filtros por metadata).                      |
# - Parámetros de modelos (embeddings y LLM) leídos desde variables de entorno. |
#                                                                               |
# Propósito:                                                                    |
# - Evitar valores “hardcodeados” en el resto del proyecto.                     |
# - Permitir cambiar el comportamiento del pipeline desde un solo lugar.        |
# ==============================================================================|
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PDFS_PATH = Path("data/raw/")
PDFJS_PATH = Path("docs/pdfjs/")
PAGES_FILE = Path("data/processed/pages.jsonl")
CHUNKS_FILE = Path("data/processed/chunks.jsonl")
CHROMA_PATH = Path("vector_store")
BATCH_SIZE = 128
EMBED_MODEL = "text-embedding-3-small"
TOP_K = 10
LLM_MODEL = "gpt-4o-mini"
PER_DAY_LIMIT = 70
WINDOW_DAY = 86400
PER_MINUTE_LIMIT = 20
WINDOW_MIN = 60
MAX_TOKENS_STRICT = 600
MAX_TOKENS_EXPLANATORY = 1200
PDF_PER_MINUTE_LIMIT = 30
PDF_PER_DAY_LIMIT = 500