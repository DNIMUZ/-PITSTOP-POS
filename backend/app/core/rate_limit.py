"""SlowAPI rate limiter shared instance.

Rate limits are configured with environment variables so the limit can be
raised per environment. Exempts the testing environment so tests do not
flakily trigger rate limits (except dedicated rate-limit tests).
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, enabled=True)
