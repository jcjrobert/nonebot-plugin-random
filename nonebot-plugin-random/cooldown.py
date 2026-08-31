from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


CooldownKey = Tuple[str, str]


@dataclass(frozen=True)
class CooldownLease:
    key: Optional[CooldownKey]
    token: int


class GroupCooldownManager:
    def __init__(self) -> None:
        self._entries: Dict[CooldownKey, Tuple[float, int]] = {}
        self._lock = asyncio.Lock()
        self._token = 0

    async def acquire(
        self,
        pool_id: str,
        group_id: str,
        cooldown_seconds: int,
    ) -> Optional[CooldownLease]:
        if cooldown_seconds <= 0:
            return CooldownLease(key=None, token=0)

        now = time.monotonic()
        key = (pool_id, group_id)
        async with self._lock:
            self._prune(now)
            current = self._entries.get(key)
            if current and current[0] > now:
                return None
            self._token += 1
            token = self._token
            self._entries[key] = (now + cooldown_seconds, token)
            return CooldownLease(key=key, token=token)

    async def release(self, lease: Optional[CooldownLease]) -> None:
        if lease is None or lease.key is None:
            return
        async with self._lock:
            current = self._entries.get(lease.key)
            if current and current[1] == lease.token:
                self._entries.pop(lease.key, None)

    async def clear_pool(self, pool_id: str) -> None:
        async with self._lock:
            keys = [key for key in self._entries if key[0] == pool_id]
            for key in keys:
                self._entries.pop(key, None)

    def _prune(self, now: float) -> None:
        expired = [key for key, value in self._entries.items() if value[0] <= now]
        for key in expired:
            self._entries.pop(key, None)


group_cooldowns = GroupCooldownManager()
