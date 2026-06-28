"""In-memory rate limiting for PregAI chatbot"""
import time
from collections import deque
from typing import Dict, Tuple
from backend.config.settings import settings


class RateLimiter:
    """
    Simple in-memory rate limiter to replace Redis.
    Uses sliding window for minute limits and daily tracking.
    """

    def __init__(self):
        self.minute_limit = settings.openrouter_minute_limit
        self.daily_limit = settings.openrouter_daily_limit
        self.user_calls: Dict[str, deque] = {}
        self.daily_calls: Dict[str, Tuple[int, str]] = {}

    def is_allowed(self, user_id: str) -> Tuple[bool, str]:
        """Check if request is allowed for the user"""
        now = time.time()
        current_day = time.strftime('%Y-%m-%d', time.gmtime(now))

        count, last_day = self.daily_calls.get(user_id, (0, ''))
        if last_day != current_day:
            count = 0

        if count >= self.daily_limit:
            return False, 'Daily limit reached. Please try again tomorrow.'

        if user_id not in self.user_calls:
            self.user_calls[user_id] = deque()

        window_start = now - 60
        while self.user_calls[user_id] and self.user_calls[user_id][0] < window_start:
            self.user_calls[user_id].popleft()

        if len(self.user_calls[user_id]) >= self.minute_limit:
            return False, 'Rate limit exceeded. Please wait a minute before sending another message.'

        self.user_calls[user_id].append(now)
        self.daily_calls[user_id] = (count + 1, current_day)

        return True, ''


rate_limiter = RateLimiter()