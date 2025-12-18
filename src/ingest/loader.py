# Design note:
# Metadata inference is handled within loader.py to keep the ingestion
# pipeline simple. The loader is the single source of truth for
# document/page metadata.
"""
Loader de documentos (PDF -> páginas).

Responsabilidad:
- Leer PDFs desde data/raw y extraer texto por página.
- Adjuntar metadata base por documento y página (ej. año, tipo de documento,
  auditado/no auditado, fuente, página).
- Entregar una salida trazable (page-level) para habilitar citas precisas.

No hace:
- No limpia agresivamente el texto (eso es del cleaner).
- No crea chunks (eso es del splitter).
- No genera embeddings ni escribe al vector store (eso es del build_index).
"""
