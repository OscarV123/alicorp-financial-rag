"""
Plantillas y reglas de prompting para el RAG.

Responsabilidad:
- Definir cómo se le pide al modelo que responda usando evidencia (grounding).
- Establecer reglas para evitar alucinaciones:
  - no inventar si no hay evidencia
  - no mezclar años o fuentes
  - incluir citas (documento/página) cuando sea posible

No hace:
- No recupera documentos.
- No llama directamente al vector store.
"""
