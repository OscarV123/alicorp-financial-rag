# ===============================================================================l
# Plantillas y reglas de prompting para el RAG.                                  |
#                                                                                |
# Responsabilidad:                                                               |
# - Definir cómo se le pide al modelo que responda usando evidencia (grounding). |
# - Establecer reglas para evitar alucinaciones:                                 |
#   - no inventar si no hay evidencia                                            |
#   - no mezclar años o fuentes                                                  |
#   - incluir citas (documento/página) cuando sea posible                        |
#                                                                                | 
# No hace:                                                                       |
# - No recupera documentos.                                                      |
# - No llama directamente al vector store.                                       |
# ===============================================================================|
from typing import Dict, Any, List

SYSTEM_RULES = """\
Eres un asistente de QA financiero. Responde SOLO usando la evidencia proporcionada.
REGLAS ESTRICTAS:
1) No inventes datos. Si la evidencia no alcanza, di: "No hay evidencia suficiente en los fragmentos proporcionados."
2) No mezcles años, cifras o entidades de diferentes fuentes. Mantén consistencia por documento y página.
3) No asumas ni extrapoles (ej. "probablemente", "seguro"). Solo hechos soportados.
4) Si la pregunta pide un valor exacto y no aparece literal en la evidencia, dilo claramente.
5) Cada afirmación importante debe incluir cita al final en este formato:
   (doc_id, pág. X)
6) Si hay varias fuentes para una misma idea, puedes citar varias:
   (docA, pág. X; docB, pág. Y)
7) Si hay conflicto entre fuentes, repórtalo y cita ambas.
8) No uses conocimiento externo. No uses tu memoria. Solo el contexto.
9) Responde en español, tono profesional y claro.
10) Si presentas múltiples hechos, cada uno debe tener su propia cita inmediata.
"""

USER_TEMPLATE = USER_TEMPLATE = """\
PREGUNTA: {question}
EVIDENCIA (fragmentos): {context}
INSTRUCCIONES:
- Responde únicamente usando la evidencia proporcionada.
- No infieras, no asumas, no extrapoles información.
- No utilices conocimiento externo ni tu memoria.
- No mezcles datos (años, cifras, entidades) de diferentes documentos o páginas.
- Cada afirmación relevante debe incluir su cita inmediatamente al final en este formato:
  (doc_id, pág. X)
- Si la pregunta solicita un dato exacto que no aparece literalmente en la evidencia,
  responde exactamente:
  "No hay evidencia suficiente en los fragmentos proporcionados."
- Responde en español, con tono profesional y claro.
"""

def format_citation(meta: Dict[str, Any]):
    doc_id = meta.get("doc_id", "N/A")
    page = meta.get("page_number", "N/A")

    return f"({doc_id}, pág. {page})"

def build_context(evidences: List[Any], max_chars_per_chunk: int = 1600) -> str:
    parts: List[str] = []

    for i, ev in enumerate(evidences, start=1):
        meta = ev.metadata if hasattr(ev, "metadata") else ev.get("metadata", {})
        text = ev.text if hasattr(ev, "text") else ev.get("text", "")

        doc_id = meta.get("doc_id", "N/A")
        year = meta.get("year", "N/A")
        doc_type = meta.get("doc_type", "N/A")
        page = meta.get("page_number", "N/A")
        chunk_id = meta.get("chunk_id", "N/A")

        if max_chars_per_chunk and len(text) > max_chars_per_chunk:
            text = text[:max_chars_per_chunk] + "…"

        parts.append(
            f"[Fuente {i}] "
            f"doc_id={doc_id} | año={year} | tipo={doc_type} | página={page} | chunk_id={chunk_id}\n"
            f"{text}\n"
        )

    return "\n".join(parts).strip()
