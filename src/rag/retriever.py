"""
Retriever (pregunta -> evidencia relevante).

Responsabilidad:
- Recibir una pregunta y recuperar los chunks más relevantes desde el vector store.
- Aplicar reglas de búsqueda y/o filtros por metadata (ej. año, tipo de documento).
- Devolver evidencia lista para ser usada como contexto por el generador.

No hace:
- No redacta la respuesta final (eso es del QA).
- No define la política de respuesta (eso es del prompt).
"""
