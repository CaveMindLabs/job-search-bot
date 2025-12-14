# api/dependencies.py

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from core.config import get_settings

settings = get_settings()

# Define the header we expect the API key to be in
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    """
    Dependency function to verify the API key in the request header.
    """
    if api_key == settings.INTERNAL_API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
