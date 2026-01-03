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
#from src.rag.retriever import retrieve, Evidence
import src.rag.retriever as retriever
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Tuple
import src.rag.prompt as prompt
import src.config as config
from openai import OpenAI

@dataclass
class QAResult:
    answer: str
    evidences: List[retriever.Evidence]
  
def build_messages(question: str, evidences: List[retriever.Evidence], mode: str="strict") -> List[Dict[str, str]]:
    context = prompt.build_context(evidences)
    mode = (mode or "strict").strip().lower()
    
    if mode not in ("strict", "explanatory"):
        mode = "strict"
    
    system_rules: str = ""
    
    if mode == "strict":
        system_rules = prompt.SYSTEM_RULES_BASE + prompt.SYSTEM_RULES_STRICT_ADDON
    else:
        system_rules = prompt.SYSTEM_RULES_BASE + prompt.SYSTEM_RULES_EXPLANATORY_ADDON
    
    user_content = prompt.USER_TEMPLATE.format(
        mode=mode,
        question=question.strip(),
        context=context      
    )
    
    return [
        {"role": "system", "content": system_rules},
        {"role": "user", "content": user_content}
    ]
    
def answer_question(question: str,
                    top_k: int=config.TOP_K,
                    where: Optional[Dict[str, Any]]=None,
                    temperature: float=0.1,
                    mode: str="strict") -> QAResult:
    if not config.API_KEY:
        raise ValueError("API_KEY no está configurada. Por favor, configure la clave de API para el LLM.")
    
    evidences = retriever.retrieve(question, top_k=top_k, where=where, return_debug=False)
              
    if isinstance(evidences, Tuple):
        evidences, _ = evidences
        print("\n=== DEBUG detect_signals ===")
        print("key:", _.key)
        print("score:", _.score)
        print("where:", _.where)
        print("debug:", _.debug)
              
    if not evidences:
        return QAResult(
            answer="Lo siento, no pude encontrar información relevante para responder a su pregunta.",
            evidences=[]
        )
    
    messages = build_messages(question, evidences, mode)
    
    client = OpenAI(api_key=config.API_KEY)
    response = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=messages,
        temperature=temperature
    )
    
    answer = (response.choices[0].message.content or "").strip()
    
    return QAResult(answer=answer, evidences=evidences)