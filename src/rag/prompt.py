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
1) No inventes datos.
   - Si la pregunta es clara y la evidencia no alcanza, responde EXACTAMENTE: "No hay evidencia suficiente en los fragmentos proporcionados."
   - NO agregues texto adicional.
2) No mezcles años, cifras o entidades de diferentes fuentes. Mantén consistencia por documento y página.
3) No asumas ni extrapoles (ej. "probablemente", "seguro"). Solo hechos soportados.
4) Si la pregunta pide un valor exacto y no aparece literal en la evidencia, aplica la regla 1.
5) Cada afirmación importante debe incluir cita inmediata al final en este formato:
   (nombre del documento, pág. X)
5.1) Comparaciones: si afirmas ausencia o novedad ("no aparece en 2022", "es nueva en 2023"), DEBES citar evidencia de ambos lados (año/documento A y B). Si falta evidencia de alguno, responde:
   "No hay evidencia suficiente en los fragmentos proporcionados." y solicita más contexto sobre documento, año, etc
6) Si hay varias fuentes para la misma idea, puedes citar varias:
   (doc1, pág. X; doc2, pág. Y)
7) Si hay conflicto entre fuentes, repórtalo y cita ambas.
8) No uses conocimiento externo. No uses tu memoria. Solo el contexto.
9) Responde en español, tono profesional y claro.
10) Si presentas múltiples hechos, cada uno debe tener su propia cita inmediata.

REGLAS DE ALCANCE (SCOPE):
11) Si la pregunta especifica un documento (ej. "Reporte 4T-2024"), responde SOLO con ese documento. Si no hay evidencia dentro de ese documento, aplica la regla 1.
REGLAS DE AMBIGÜEDAD (REALIZA PREGUNTAS DE ACLARACIÓN):
12) Si la pregunta NO especifica claramente:
    - el documento,
    - el año,
    - o el tipo de operación (ej. recompra de acciones vs bonos),
    NO respondas.
    Formula UNA (1) pregunta breve de aclaración y espera respuesta.
REGLAS NUMÉRICAS:
13) No redondees cifras ni cambies unidades. Respeta la moneda y la escala (S/, USD, miles, millones) tal como aparece en la evidencia.
"""

USER_TEMPLATE = """\
PREGUNTA: {question}
EVIDENCIA (fragmentos): {context}
INSTRUCCIONES:
- Responde únicamente usando la evidencia proporcionada.
- No infieras, no asumas, no extrapoles información.
- No utilices conocimiento externo ni tu memoria.
- NO MEZCLES DATOS (años, cifras, entidades) de diferentes documentos o páginas.
- Cada afirmación relevante debe incluir su cita inmediatamente al final:
  (nombre del documento, pág. X)
MANEJO DE AMBIGÜEDAD (ACLARACIÓN):
- Si la pregunta NO especifica claramente el documento y hay más de una fuente posible, o si el término es ambiguo
  (ej. "recompra" puede ser acciones o bonos), NO respondas con datos.
  Formula UNA (1) pregunta breve de aclaración y espera.
RECHAZO POR FALTA DE EVIDENCIA:
- Si la pregunta es clara y solicita un dato exacto que NO aparece literalmente en la evidencia, responde EXACTAMENTE:
  "No hay evidencia suficiente en los fragmentos proporcionados."
- No agregues texto adicional después de esa frase.
"""



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
