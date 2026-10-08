import asyncio
import time
import pytest
from services.rate_limiter import AsyncTokenBucket


@pytest.mark.asyncio
async def test_rate_limiter_does_not_hold_lock_during_sleep() -> None:
    """
    Proves that a waiting request does not hold self._lock while awaiting asyncio.sleep,
    allowing unrelated operations to proceed immediately.
    """
    # 1 token capacity, fills 0.5 tokens/sec (i.e. 2 seconds per token)
    limiter = AsyncTokenBucket(capacity=1, fill_rate=0.5)
    
    # Drain initial token immediately
    await limiter.consume(1)
    assert limiter.tokens == 0.0

    # Task 1 needs 1 token, requiring ~2.0 seconds wait
    t1 = asyncio.create_task(limiter.consume(1))

    # Give Task 1 a slice of the event loop to acquire lock, calculate wait, release lock, and enter sleep
    await asyncio.sleep(0.05)

    # CRITICAL INVARIANT: The lock must NOT be held while Task 1 is sleeping!
    assert not limiter._lock.locked(), "Failure: Rate limiter held async lock during sleep!"

    # An unrelated operation can acquire the lock immediately without waiting 2 seconds
    start_time = time.monotonic()
    async def unrelated_operation() -> str:
        async with limiter._lock:
            return "unblocked"

    result = await asyncio.wait_for(unrelated_operation(), timeout=0.2)
    elapsed = time.monotonic() - start_time

    assert result == "unblocked"
    assert elapsed < 0.2, f"Operation took too long ({elapsed}s), was unexpectedly blocked by sleeping task!"

    # Clean up background task
    t1.cancel()
    try:
        await t1
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_rate_limiter_concurrent_consumption_integrity() -> None:
    """
    Verifies state remains correct under concurrent requests.
    """
    # Fast fill rate for quick test execution
    limiter = AsyncTokenBucket(capacity=2, fill_rate=20.0)

    # 4 concurrent consumers of 1 token each
    async def worker(idx: int) -> int:
        await limiter.consume(1)
        return idx

    results = await asyncio.gather(*(worker(i) for i in range(4)))
    assert len(results) == 4
    assert sorted(results) == [0, 1, 2, 3]
