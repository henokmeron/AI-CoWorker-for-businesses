"""
Authentication API routes.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from ...core.config import settings
from ...core.security import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    success: bool
    message: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    token: Optional[str] = None


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Login with email and password.
    
    In production, this would:
    1. Verify credentials against database
    2. Generate JWT token
    3. Return user info and token
    """
    try:
        logger.info(f"Login attempt for: {request.email}")
        
        # For demo: Accept any email with any non-empty password
        # In production: Verify against database, hash passwords, etc.
        if not request.password or len(request.password.strip()) == 0:
            logger.warning(f"Login failed: Empty password for {request.email}")
            raise HTTPException(status_code=401, detail="Password cannot be empty")
        
        # Validate email format (Pydantic already does this, but double-check)
        if "@" not in request.email:
            logger.warning(f"Login failed: Invalid email format: {request.email}")
            raise HTTPException(status_code=401, detail="Invalid email format")
        
        # Extract username from email
        username = request.email.split("@")[0].title()
        
        # In production, generate JWT token here
        # token = create_access_token(data={"sub": request.email})
        
        logger.info(f"Login successful for: {request.email}")
        return LoginResponse(
            success=True,
            message="Login successful",
            user_id=f"user_{request.email}",
            user_name=username,
            user_email=request.email,
            token="demo_token"  # Replace with real JWT
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.get("/google")
async def google_oauth(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    Initiate Google OAuth flow.
    
    In production, this would redirect to Google OAuth.
    """
    # TODO: Implement Google OAuth
    # For now, return info message
    logger.info("Google OAuth requested")
    return {
        "message": "Google OAuth integration coming soon",
        "oauth_url": "https://accounts.google.com/o/oauth2/v2/auth"  # Placeholder
    }


@router.get("/microsoft")
async def microsoft_oauth(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    Initiate Microsoft OAuth flow.
    
    In production, this would redirect to Microsoft OAuth.
    """
    # TODO: Implement Microsoft OAuth
    logger.info("Microsoft OAuth requested")
    return {
        "message": "Microsoft OAuth integration coming soon",
        "oauth_url": "https://login.microsoftonline.com/oauth2/v2.0/authorize"  # Placeholder
    }


@router.post("/logout")
async def logout(
    api_key: str = Depends(verify_api_key)
):
    """Logout user."""
    # In production, invalidate token
    return {"success": True, "message": "Logged out successfully"}


@router.get("/me")
async def get_current_user(
    api_key: str = Depends(verify_api_key)
):
    """Get current user info."""
    # In production, decode JWT and return user info
    return {
        "user_id": "demo_user",
        "user_name": "Demo User",
        "user_email": "demo@example.com"
    }

