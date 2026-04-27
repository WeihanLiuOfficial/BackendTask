"""Rate limiting middleware using slowapi.

Protects the AI generation endpoint from abuse by enforcing
per-IP request limits. The limiter instance is attached to the
FastAPI application state in main.py.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Initialize the rate limiter with IP-based key extraction
limiter = Limiter(key_func=get_remote_address)

# The rate limit string (e.g., "10/minute") is sourced from settings.
# Apply to specific routes using the @limiter.limit() decorator.
# Example usage in a route handler:
#   @router.post("/generate")
#   @limiter.limit(settings.RATE_LIMIT)
#   async def generate_survey(request: Request, ...):
