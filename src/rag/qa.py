"""
Orquestador de QA (pregunta -> respuesta con citas).

Responsabilidad:
- Coordinar el flujo runtime del RAG:
  1) recuperar evidencia (retriever)
  2) construir contexto (texto + metadata/citas)
  3) aplicar prompt (política de respuesta)
  4) invocar el LLM y formatear la respuesta final

No hace:
- No indexa documentos (eso es ingest/build_index).
- No modifica el vector store.
"""
