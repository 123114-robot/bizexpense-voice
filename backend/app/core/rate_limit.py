from collections import defaultdict, deque
from collections.abc import Callable
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = monotonic):
        self._clock = clock
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def consume(self, key: str, limit: int, window_seconds: int) -> int | None:
        now = self._clock()
        cutoff = now - window_seconds
        with self._lock:
            requests = self._requests[key]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= limit:
                return max(1, ceil(requests[0] + window_seconds - now))
            requests.append(now)
        return None

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


class RateLimitDependency:
    def __init__(self, scope: str, limit: int, window_seconds: int):
        self.scope = scope
        self.limit = limit
        self.window_seconds = window_seconds

    def __call__(self, request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        key = f"{self.scope}:{client}"
        retry_after = rate_limiter.consume(key, self.limit, self.window_seconds)
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={"Retry-After": str(retry_after)},
            )


rate_limiter = RateLimiter()
