"""함수 실행 시간을 밀리초 단위로 측정하는 데코레이터.

동기/비동기 함수 모두 지원하며, 원래 반환값과 함께
(result, latency_ms) 튜플로 결과를 돌려준다.
"""

import time
import functools
from typing import Any


def measure_time(func):
    """동기/비동기 함수의 실행 시간(ms)을 측정하여 (result, latency_ms) 튜플로 반환.

    사용 예:
        @measure_time
        async def call_api(): ...
        result, ms = await call_api()
    """

    if _is_coroutine_function(func):
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> tuple[Any, float]:
            start = time.perf_counter()  # 고해상도 타이머 시작
            result = await func(*args, **kwargs)
            latency_ms = (time.perf_counter() - start) * 1000  # 초 → 밀리초 변환
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
    """함수가 async 코루틴인지 판별."""
    import asyncio
    return asyncio.iscoroutinefunction(func)
