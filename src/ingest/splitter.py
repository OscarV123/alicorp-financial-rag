"""
Chunking (páginas -> chunks).

Responsabilidad:
- Transformar texto a nivel de página en fragments/chunks con solapamiento.
- Preservar trazabilidad: cada chunk debe poder mapearse a una página o rango de páginas.
- Heredar metadata base y añadir metadata propia del chunk (chunk_id, page_start/page_end).

No hace:
- No genera embeddings.
- No escribe en el vector store.
"""
