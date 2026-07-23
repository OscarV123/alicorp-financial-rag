import time
from threading import Lock
from fastapi import HTTPException, Request
from collections import defaultdict, deque
from src.config import WINDOW_DAY, WINDOW_MIN

_buckets = defaultdict(
    lambda: {
        "minute": deque(),
        "day": deque()        
    }
)

_lock = Lock()

def get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def _prune(q: deque, now: float, window: int) -> None:
    while q and (now - q[0]) >= window:
        q.popleft()
 
def rate_limit(request: Request, *, scope: str, per_minute_limit: int, per_day_limit: int) -> None:
    ip = get_client_ip(request)
    now = time.monotonic()

    key = (scope, ip)

    with _lock:
        bucket = _buckets[key]

        qmin = bucket["minute"]
        qday = bucket["day"]

        _prune(qmin, now, WINDOW_MIN)
        _prune(qday, now, WINDOW_DAY)

        if len(qmin) >= per_minute_limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests per minute",
                headers={"Retry-After": "60"}
            )

        if len(qday) >= per_day_limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests per day"
            )

        qmin.append(now)
        qday.append(now)