import time
from threading import Lock
from fastapi import HTTPException, Request
from collections import deque
from src.config import WINDOW_DAY, WINDOW_MIN
from ipaddress import ip_address

_buckets: dict[tuple[str, str], dict[str, deque]] = {}

CLEANUP_INTERVAL = 600
MAX_BUCKETS = 2000
_last_cleanup = 0.0

_lock = Lock()

def get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")

    candidate = (
        xff.split(",")[-1].strip()
        if xff
        else request.client.host if request.client else "unknown"
    )

    try:
        return str(ip_address(candidate))
    except ValueError:
        return "unknown"

def _prune(q: deque, now: float, window: int) -> None:
    while q and (now - q[0]) >= window:
        q.popleft()

def _cleanup_buckets(now: float) -> None:
    global _last_cleanup

    if (now - _last_cleanup) < CLEANUP_INTERVAL:
        return

    expired_keys = []

    for key, bucket in _buckets.items():
        _prune(bucket["minute"], now, WINDOW_MIN)
        _prune(bucket["day"], now, WINDOW_DAY)

        if not bucket["minute"] and not bucket["day"]:
            expired_keys.append(key)

    for key in expired_keys:
        _buckets.pop(key, None)

    _last_cleanup = now
 
def rate_limit(request: Request, *, scope: str, per_minute_limit: int, per_day_limit: int) -> None:
    ip = get_client_ip(request)
    now = time.monotonic()

    key = (scope, ip)

    with _lock:
        _cleanup_buckets(now)

        bucket = _buckets.get(key)

        if bucket is None:
            if len(_buckets) >= MAX_BUCKETS:
                raise HTTPException(
                    status_code=429,
                    detail="Too many distinct clients",
                    headers={"Retry-After": "60"}
                )

            bucket = {
                "minute": deque(),
                "day": deque()
            }

            _buckets[key] = bucket

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