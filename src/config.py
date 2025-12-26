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
import os

PDFS_PATH = Path("data/raw/")
PAGES_FILE = Path("data/processed/pages.jsonl")
CHUNKS_FILE = Path("data/processed/chunks.jsonl")
CHROMA_PATH = Path("vector_store")
API_KEY = os.getenv("OPENAI_API_KEY")
BATCH_SIZE = 128
EMBED_MODEL = "text-embedding-3-small"
TOP_K = 5
LLM_MODEL = "gpt-4o-mini"