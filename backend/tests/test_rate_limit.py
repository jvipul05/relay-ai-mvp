from app.core.rate_limit import SlidingWindowRateLimiter


def test_sliding_window_rejects_over_limit_then_recovers():
    limiter = SlidingWindowRateLimiter(window_seconds=10)
    assert limiter.check("demo-client", 2, now=100) == (True, 0)
    assert limiter.check("demo-client", 2, now=101) == (True, 0)
    assert limiter.check("demo-client", 2, now=102) == (False, 8)
    assert limiter.check("demo-client", 2, now=110) == (True, 0)


def test_rate_limits_are_isolated_by_key():
    limiter = SlidingWindowRateLimiter(window_seconds=60)
    assert limiter.check("client-a", 1, now=50) == (True, 0)
    assert limiter.check("client-a", 1, now=51)[0] is False
    assert limiter.check("client-b", 1, now=51) == (True, 0)
