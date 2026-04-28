"""Bearer token authentication middleware (Option B: disabled by default).

When API_BEARER_TOKEN is set to 'disabled' (the default in .env.example),
all endpoints are accessible without authentication. When set to any other
value, all protected endpoints require the matching Bearer token.

This design ensures:
- Zero friction for interviewers cloning the repo
- Full auth capability when explicitly enabled
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

# Security scheme for OpenAPI documentation
# auto_error=False allows us to handle missing tokens gracefully
security_scheme = HTTPBearer(auto_error=False)


async def verify_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[str]:
    """Validate the Bearer token from the Authorization header.

    If API_BEARER_TOKEN is set to 'disabled', authentication is skipped
    entirely and all requests are permitted.

    Args:
        credentials: The extracted Bearer token from the request (or None).

    Returns:
        The validated token string, or None if auth is disabled.

    Raises:
        HTTPException(401): If auth is enabled and the token is missing or invalid.
    """
    # Option B: If token is 'disabled', skip authentication entirely
    if settings.API_BEARER_TOKEN.lower() == "disabled":
        return None

    # Auth is enabled — token is required
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != settings.API_BEARER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
