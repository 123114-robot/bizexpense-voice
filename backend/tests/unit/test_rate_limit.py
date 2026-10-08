from app.core.rate_limit import RateLimiter


def test_rate_limiter_blocks_until_window_expires():
    now = [100.0]
    limiter = RateLimiter(clock=lambda: now[0])

    assert limiter.consume("login:client", limit=2, window_seconds=60) is None
    assert limiter.consume("login:client", limit=2, window_seconds=60) is None
    assert limiter.consume("login:client", limit=2, window_seconds=60) == 60

    now[0] = 161.0
    assert limiter.consume("login:client", limit=2, window_seconds=60) is None


def test_rate_limiter_keeps_clients_isolated():
    limiter = RateLimiter(clock=lambda: 100.0)

    assert limiter.consume("login:first", limit=1, window_seconds=60) is None
    assert limiter.consume("login:first", limit=1, window_seconds=60) == 60
    assert limiter.consume("login:second", limit=1, window_seconds=60) is None
