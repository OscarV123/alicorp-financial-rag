"""
Indexación (chunks -> embeddings -> vector store).

Responsabilidad:
- Tomar los chunks ya preparados y construir/actualizar la base vectorial.
- Persistir embeddings + metadata en vector_store para consultas posteriores.
- Ejecutarse como proceso de ingesta (offline/batch), no en cada pregunta.

No hace:
- No responde preguntas.
- No invoca el LLM para generar respuestas.
"""
