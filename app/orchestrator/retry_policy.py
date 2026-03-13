"""Retry Policy — API 실패·Judge escalate 등의 재시도/폴백 정책.

tenacity를 보완하는 정책 레이어로, 재시도 횟수·지수 백오프·
최종 실패 시 처리를 통합 관리한다.
"""

import math


class RetryPolicy:
    """재시도 횟수, 지수 백오프, 최종 실패 처리를 통합 관리하는 정책 클래스."""

    def __init__(
        self,
        max_retries: int = 3,       # 최대 재시도 횟수
        backoff_base: float = 1.0,  # 백오프 기본 대기 시간 (초)
        backoff_max: float = 30.0,  # 백오프 최대 대기 시간 (초)
    ):
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.failure_log: list[dict] = []  # 실패 이력 기록

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """현재 시도 횟수 기준으로 재시도 여부를 판단.

        Args:
            error: 발생한 예외
            attempt: 현재 시도 번호 (1부터 시작)

        Returns:
            재시도 가능 여부
        """
        if attempt >= self.max_retries:
            return False

        # 재시도 가능한 에러 유형 판별
        error_name = type(error).__name__
        retryable_errors = {
            "HTTPStatusError",   # 429, 500, 502, 503 등
            "ConnectError",      # 네트워크 연결 실패
            "TimeoutException",  # 요청 타임아웃
            "ReadTimeout",       # 읽기 타임아웃
        }
        return error_name in retryable_errors

    def get_delay(self, attempt: int) -> float:
        """지수 백오프 대기 시간을 계산 (초).

        delay = min(backoff_base * 2^attempt, backoff_max)
        """
        delay = self.backoff_base * math.pow(2, attempt)
        return min(delay, self.backoff_max)

    def on_final_failure(self, error: Exception, context: dict) -> None:
        """최대 재시도 후에도 실패한 경우의 처리.

        실패 이력을 기록하고, 이후 분석에 활용.
        """
        self.failure_log.append({
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
        })

    def reset(self) -> None:
        """실패 이력 초기화."""
        self.failure_log.clear()
