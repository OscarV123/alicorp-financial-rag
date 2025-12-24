# ======================================================
# Orquestador de QA (pregunta -> respuesta con citas). |
#                                                      |
# Responsabilidad:                                     | 
# - Coordinar el flujo runtime del RAG:                |
#   1) recuperar evidencia (retriever)                 |
#   2) construir contexto (texto + metadata/citas)     |
#   3) aplicar prompt (política de respuesta)          |
#   4) invocar el LLM y formatear la respuesta final   |
#                                                      |
# No hace:                                             |
# - No indexa documentos (eso es ingest/build_index).  |
# - No modifica el vector store.                       |  
# =====================================================|
from src.rag.retriever import retrieve, Evidence
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from src.rag.prompt import build_context, USER_TEMPLATE, SYSTEM_RULES
from src.config import TOP_K, API_KEY, LLM_MODEL
from openai import OpenAI

@dataclass
class QAResult:
    answer: str
    evidences: List[Evidence]
  
def build_messages(question: str, evidences: List[Evidence]) -> List[Dict[str, str]]:
    context = build_context(evidences)
    
    user_content = USER_TEMPLATE.format(
        question=question.strip(),
        context=context      
    )
    
    return [
        {"role": "system", "content": SYSTEM_RULES},
        {"role": "user", "content": user_content}
    ]
    
def answer_question(question: str, top_k: int=TOP_K, where: Optional[Dict[str, Any]]=None, temperature: float=0.1) -> QAResult:
    if not API_KEY:
        raise ValueError("API_KEY no está configurada. Por favor, configure la clave de API para el LLM.")
    
    evidences = retrieve(question, top_k=top_k, where=where)
    
    if not evidences:
        return QAResult(
            answer="Lo siento, no pude encontrar información relevante para responder a su pregunta.",
            evidences=[]
        )
    
    messages = build_messages(question, evidences)
    
    client = OpenAI(api_key=API_KEY)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=temperature
    )
    
    answer = (response.choices[0].message.content or "").strip()
    
    return QAResult(answer=answer, evidences=evidences)