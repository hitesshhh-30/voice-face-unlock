"""Failure counting + cooldown so nobody can just keep trying."""
from __future__ import annotations

import time
from collections.abc import Callable


class Guard:
    def __init__(self, max_failures: int, cooldown_s: float, clock: Callable[[], float] = time.monotonic):
        self.max_failures, self.cooldown_s, self.clock = max_failures, cooldown_s, clock
        self.failures = 0
        self.blocked_until = 0.0

    def blocked(self) -> bool:
        return self.clock() < self.blocked_until

    def fail(self) -> bool:
        """Record a failure. Returns True if this failure started a cooldown."""
        self.failures += 1
        if self.failures >= self.max_failures:
            self.failures = 0
            self.blocked_until = self.clock() + self.cooldown_s
            return True
        return False

    def success(self) -> None:
        self.failures = 0
