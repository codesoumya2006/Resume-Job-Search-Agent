import asyncio
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class AsyncTokenBucket:
    def __init__(self, capacity: int, fill_rate: float):
        """
        capacity: Maximum tokens the bucket can hold.
        fill_rate: Tokens added per second.
        """
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_fill = time.monotonic()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: int = 1):
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_fill
                self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
                self.last_fill = now

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                else:
                    # Calculate wait time
                    wait_time = (tokens - self.tokens) / self.fill_rate
                    await asyncio.sleep(wait_time)

# Shared rate limiters per domain (e.g., 1 request per 2 seconds)
LINKEDIN_LIMITER = AsyncTokenBucket(capacity=1, fill_rate=0.5)
NAUKRI_LIMITER = AsyncTokenBucket(capacity=1, fill_rate=0.5)
INTERNSHALA_LIMITER = AsyncTokenBucket(capacity=1, fill_rate=0.5)
INDEED_LIMITER = AsyncTokenBucket(capacity=1, fill_rate=0.5)

def with_retry_and_fallback(limiter: AsyncTokenBucket, max_retries: int = 3):
    """
    Wraps an async function with rate limiting, retry with exponential backoff,
    and graceful fallback returning an empty list on persistent failures.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                await limiter.consume(1)
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Error in {func.__name__} (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
            logger.error(f"All {max_retries} attempts failed in {func.__name__}. Gracefully returning empty list.")
            return []
        return wrapper
    return decorator
