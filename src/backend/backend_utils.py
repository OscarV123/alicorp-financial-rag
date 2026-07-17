from fastapi import HTTPException, Request
import time
from collections import defaultdict, deque
from src.config import DAILY_LIMIT, PER_MINUTE_LIMIT, WINDOW_DAY, WINDOW_MIN

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
    

