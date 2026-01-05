"""
Security utilities for API authentication.
"""

from fastapi import Depends, HTTPException, status, Header
from config import API_KEY_ENABLED, API_KEYS
from src.logging import setup_logger
from src.database import get_session, close_session
from src.database.models import UserModel
from datetime import datetime

logger = setup_logger(__name__)


async def verify_api_key(authorization: str = Header(None)) -> str:
    """
    Verify API key from request header.
    
    Args:
        authorization: Authorization header (Bearer <API_KEY>)
    
    Returns:
        User ID if valid
    
    Raises:
        HTTPException: If API key is invalid
    """
    if not API_KEY_ENABLED:
        return "anonymous"

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )

    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    api_key = parts[1]

    # Check in database
    session = get_session()
    try:
        user = session.query(UserModel).filter(
            UserModel.api_key == api_key,
            UserModel.is_active == "active"
        ).first()

        if not user:
            logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or inactive API key"
            )

        # Update last used
        user.last_used = datetime.utcnow()
        session.commit()
        logger.info(f"API key used by user: {user.username}")
        return user.id

    finally:
        close_session(session)


async def verify_permission(user_id: str, permission: str) -> bool:
    """
    Check if user has specific permission.
    
    Args:
        user_id: User ID
        permission: Permission string (e.g., 'submit', 'read', 'admin')
    
    Returns:
        True if user has permission
    """
    session = get_session()
    try:
        user = session.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            return False
        
        permissions = user.permissions.split(",")
        return permission in permissions or "admin" in permissions
    finally:
        close_session(session)
