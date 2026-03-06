"""함수 실행 시간을 밀리초 단위로 측정하는 데코레이터."""

import time
import functools
from typing import Any


def measure_time(func):
    """동기/비동기 함수의 실행 시간(ms)을 측정하여 (result, latency_ms) 튜플로 반환."""

    if _is_coroutine_function(func):
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> tuple[Any, float]:
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> tuple[Any, float]:
            start = time.perf_counter()
            result = func(*args, **kwargs)
            latency_ms = (time.perf_counter() - start) * 1000
            return result, latency_ms
        return sync_wrapper


def _is_coroutine_function(func) -> bool:
    import asyncio
    return asyncio.iscoroutinefunction(func)
