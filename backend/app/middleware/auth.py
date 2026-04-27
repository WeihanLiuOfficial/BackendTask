"""Bearer token authentication middleware.

Implements a simple but effective token-based authentication scheme.
Routes that require authentication use this as a FastAPI dependency.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

# Security scheme for OpenAPI documentation
security_scheme = HTTPBearer()


async def verify_bearer_token(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> str:
    """Validate the Bearer token from the Authorization header.

    Args:
        credentials: The extracted Bearer token from the request.

    Returns:
        The validated token string.

    Raises:
        HTTPException(401): If the token is missing or invalid.
    """
    if credentials.credentials != settings.API_BEARER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials
