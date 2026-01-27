from fastapi import FastAPI
from typing import List, Dict, Any
import src.rag.qa as qa

# Usar POST, se enviara al endpoint lo siguiente:
# 
# Texto de pregunta
# top_k
# combobox de filtros
# modo strict o explanatory
# json para el multiturn

app = FastAPI(title="RAG API", version="1.0.0")

# Retorno esperado:
# {
#   Respuesta: String, 
#   Evidencias: [{ doc_id: String, page_number: int, chunk_id: String, distance: float }]
# }
#   
@app.post("/query")
async def query_endpoint(question: str, top_k: int=10, filters: List[str]=None, mode: str="strict", multiturn: Dict[str, Any]=None) -> qa.QAResult | None:
    
    question = question.strip()
    if not question:
        return None
    
    answer = qa.answer_question(question=question, top_k=top_k, explicit_where=filters, mode=mode)

    return answer
    