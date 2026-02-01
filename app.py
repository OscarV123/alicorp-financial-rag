from fastapi import FastAPI, HTTPException, status
import src.rag.qa as qa
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal, Annotated

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    top_k: Annotated[int, Field(ge=1, le=50)] = 10
    explicit_where: Optional[Dict[str, Any]] = None
    mode: Literal["strict", "explanatory"] = "strict"

app = FastAPI(title="RAG API", version="1.0.0")

    
@app.post("/query")
async def query_endpoint(req: QueryRequest) -> qa.QAResult:
    
    if req.question.strip() == "": 
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Question cannot be empty")

    try:
        return qa.answer_question(req.question,
                                req.top_k, 
                                req.explicit_where, 
                                0.1,
                                req.mode)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An error occurred while processing the request")