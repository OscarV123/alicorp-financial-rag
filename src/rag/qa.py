# ====================================================================================
# Orquestador de QA (pregunta -> respuesta con citas).                               |
# ====================================================================================
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Tuple
from openai import OpenAI

import src.config as config
import src.rag.retriever as retriever
import src.rag.prompt as prompt

@dataclass
class QAResult:
    answer: str
    evidences: List[retriever.Evidence]
  
def build_messages(question: str, evidences: List[retriever.Evidence], mode: str = "strict") -> List[Dict[str, str]]:
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
                    top_k: int = config.TOP_K,
                    explicit_where: Optional[Dict[str, Any]] = None,
                    temperature: float = 0.1,
                    mode: str = "strict") -> QAResult:
    
    evidences, match_r = retriever.retrieve(
        question, 
        top_k=top_k, 
        explicit_where=explicit_where, 
        return_debug=True
    )
    
    if "where_conflicts" in match_r.debug:
        print(f" Conflictos: {match_r.debug['where_conflicts']}")
    print("===============================\n")
              
    if not evidences:
        return QAResult(
            answer="Lo siento, no pude encontrar información relevante en los reportes financieros para responder a su pregunta.",
            evidences=[]
        )
    
    messages = build_messages(question, evidences, mode)
    
    oai_client, _ = retriever.build_index.get_clients()
    
    max_tokens = getattr(config, "MAX_TOKENS_STRICT", 512) if mode == "strict" else getattr(config, "MAX_TOKENS_EXPLANATORY", 1024)
    model_name = getattr(config, "LLM_MODEL", "gpt-4o-mini")
    
    response = oai_client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    answer = (response.choices[0].message.content or "").strip()
    
    return QAResult(answer=answer, evidences=evidences)

