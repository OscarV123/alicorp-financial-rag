from fastapi import FastAPI
import src.rag.qa as qa
from pydantic import BaseModel
from typing import Optional, Dict, Any

class QueryRequest(BaseModel):
    question: str
    top_k: int = 10
    explicit_where: Optional[Dict[str, Any]] = None
    mode: str = "strict"
    
# {
#   "question": "¿y en 2022?",
#   "top_k": 10,
#   "mode": "strict",
#   "multiturn": {
#     "messages": [
#       { "role": "user", "content": "¿Cuál fue el EBITDA en 2023?" },
#       { "role": "assistant", "content": "Según la evidencia..." },
#       { "role": "user", "content": "¿y en 2022?" }
#     ],
#     "history_window": 6
#   }
# }

app = FastAPI(title="RAG API", version="1.0.0")
    
@app.post("/query")
async def query_endpoint(req: QueryRequest) -> qa.QAResult | None:
    
    question = req.question.strip()
    if not question:
        return None
    
    answer = qa.answer_question(question,
                                req.top_k, 
                                req.explicit_where, 
                                0.1,
                                req.mode)

    return answer
    