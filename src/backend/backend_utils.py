from fastapi.security.api_key import APIKeyHeader
from fastapi import Depends, HTTPException, Request
import os, bcrypt, time
from collections import defaultdict, deque
from src.config import DAILY_LIMIT, PER_MINUTE_LIMIT, WINDOW_DAY, WINDOW_MIN

rag_api_key_header = APIKeyHeader(name="RAG-API-KEY", auto_error=False)
RAG_API_KEY_HASH = os.getenv("RAG_API_KEY_HASH", "")

def require_api_key(api_key: str = Depends(rag_api_key_header)) -> None:
    if not RAG_API_KEY_HASH:
        raise HTTPException(status_code=500, detail="API key hash not configured")

    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    ok = bcrypt.checkpw(api_key.encode("utf-8"), RAG_API_KEY_HASH.encode("utf-8"))
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
ip_day = defaultdict(lambda: deque())
ip_min = defaultdict(lambda: deque())

def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"

def _prune(q: deque, now: float, window: int):
    while q and (now - q[0]) > window:
        q.popleft()
 
def rate_limit(request: Request):
    ip = get_client_ip(request)
    now = time.monotonic()
    
    qday = ip_day[ip]    
    _prune(qday, now, WINDOW_DAY)
    if len(qday) >= DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded: too many requests per day")
    qday.append(now)
    
    qmin = ip_min[ip]
    _prune(qmin, now, WINDOW_MIN)
    if len(qmin) >= PER_MINUTE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded: too many requests per minute")
    qmin.append(now)
    

