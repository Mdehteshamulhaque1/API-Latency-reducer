"""
Minimal in-process circuit breaker for protecting primary LLM model calls.

The breaker is intentionally process-local. It is used to skip the primary
model while it is unhealthy and to allow a single half-open probe after the
cooldown period.
"""
from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Callable


class CircuitState(str, Enum):
    """Possible circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Thread-safe circuit breaker with a single-probe half-open transition."""

    def __init__(
        self,
        name: str = "default",
        *,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
        half_open_max_probes: int = 1,
        half_open_success_threshold: int = 1,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be greater than 0")
        if half_open_max_probes < 1:
            raise ValueError("half_open_max_probes must be at least 1")
        if half_open_success_threshold < 1:
            raise ValueError("half_open_success_threshold must be at least 1")

        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max_probes = half_open_max_probes
        self.half_open_success_threshold = half_open_success_threshold
        self._clock = clock
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = 0.0
        self._half_open_in_flight = 0
        self._half_open_successes = 0

    @property
    def state(self) -> CircuitState:
        """Return the current state, transitioning open-to-half-open if due."""
        with self._lock:
            self._maybe_transition_to_half_open_locked()
            return self._state

    @property
    def failure_count(self) -> int:
        """Return the current consecutive primary failure count."""
        with self._lock:
            return self._failure_count

    def allow_request(self) -> bool:
        """Return whether a primary attempt may proceed."""
        with self._lock:
            self._maybe_transition_to_half_open_locked()
            if self._state is CircuitState.CLOSED:
                return True
            if (
                self._state is CircuitState.HALF_OPEN
                and self._half_open_in_flight < self.half_open_max_probes
            ):
                self._half_open_in_flight += 1
                return True
            return False

    def record_success(self) -> None:
        """Record a successful primary attempt."""
        with self._lock:
            if self._state is CircuitState.CLOSED:
                self._failure_count = 0
                return
            if self._state is not CircuitState.HALF_OPEN:
                return

            if self._half_open_in_flight > 0:
                self._half_open_in_flight -= 1
            self._half_open_successes += 1
            if self._half_open_successes >= self.half_open_success_threshold:
                self._close_locked()
            elif self._half_open_in_flight == 0:
                self._open_locked()

    def record_failure(self) -> None:
        """Record a fallback-eligible primary failure."""
        with self._lock:
            if self._state is CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._open_locked()
            elif self._state is CircuitState.HALF_OPEN:
                self._open_locked()

    def reset(self) -> None:
        """Reset the breaker to its initial closed state."""
        with self._lock:
            self._close_locked()

    def snapshot(self) -> dict[str, object]:
        """Return a log-friendly snapshot of the breaker state."""
        with self._lock:
            self._maybe_transition_to_half_open_locked()
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "cooldown_seconds": self.cooldown_seconds,
            }

    def _maybe_transition_to_half_open_locked(self) -> None:
        if (
            self._state is CircuitState.OPEN
            and self._clock() - self._opened_at >= self.cooldown_seconds
        ):
            self._state = CircuitState.HALF_OPEN
            self._half_open_in_flight = 0
            self._half_open_successes = 0

    def _open_locked(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        self._half_open_in_flight = 0
        self._half_open_successes = 0

    def _close_locked(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_in_flight = 0
        self._half_open_successes = 0


_breakers: dict[str, CircuitBreaker] = {}
_breakers_lock = threading.Lock()


def get_circuit_breaker(name: str, **config: object) -> CircuitBreaker:
    """Return or create the process-wide breaker for a model name."""
    with _breakers_lock:
        breaker = _breakers.get(name)
        if breaker is None:
            breaker = CircuitBreaker(name=name, **config)
            _breakers[name] = breaker
        return breaker


def reset_circuit_breakers() -> None:
    """Clear the process-wide breaker registry (useful for tests)."""
    with _breakers_lock:
        _breakers.clear()
