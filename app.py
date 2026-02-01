from fastapi import FastAPI, HTTPException, status, Depends, Request
import src.rag.qa as qa
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal, Annotated
from src.ingest.build_index import get_clients
from src.backend.utils import require_api_key, rate_limit
import os

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    top_k: Annotated[int, Field(ge=1, le=50)] = 10
    explicit_where: Optional[Dict[str, Any]] = None
    mode: Literal["strict", "explanatory"] = "strict"

app = FastAPI(title="RAG ALICORP API", version="1.0.0")

@app.post("/query", response_model=qa.QAResult, dependencies=[Depends(require_api_key)])
async def query_endpoint(req: QueryRequest, request: Request) -> qa.QAResult:
    rate_limit(request)
    
    question = req.question.strip()
    
    if question == "": 
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Question cannot be empty")

    try:
        return qa.answer_question(question,
                                req.top_k, 
                                req.explicit_where, 
                                0.1,
                                req.mode)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An error occurred while processing the request")
        
@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}

@app.get("/ready")
async def readiness_check():
    try:
        _, collection = get_clients()
        api_key = os.getenv("OPENAI_API_KEY")
        
        if collection is None or not hasattr(collection, "query"):
            raise RuntimeError("ChromaDB vector store is not ready.")
        
        if not api_key:
            raise RuntimeError("OpenAI API key is not configured.")
        
        return {
                "status": "ready",
                "vector_store": "available",
                "openai_api_key": "available"
               }
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Service is not ready")
        