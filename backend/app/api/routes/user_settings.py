"""
User settings API routes.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from ...core.security import verify_api_key
from ...models.user_settings import UserSettings, UserSettingsUpdate
from ...services.user_settings_service import get_user_settings_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["user_settings"])


@router.get("/settings", response_model=UserSettings)
async def get_user_settings(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get user settings."""
    try:
        service = get_user_settings_service()
        settings = service.get_settings(user_id)
        if not settings:
            # Return default settings
            from ...models.user_settings import UserSettings
            return UserSettings(user_id=user_id)
        return settings
    except Exception as e:
        logger.error(f"Error getting user settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user settings: {str(e)}")


@router.put("/settings", response_model=UserSettings)
async def update_user_settings(
    user_id: str,
    update: UserSettingsUpdate,
    api_key: str = Depends(verify_api_key)
):
    """Update user settings."""
    try:
        service = get_user_settings_service()
        updated = service.update_settings(user_id, update)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update user settings")
        return updated
    except Exception as e:
        logger.error(f"Error updating user settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update user settings: {str(e)}")


@router.delete("/settings")
async def delete_user_settings(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Delete user settings (reset to defaults)."""
    try:
        service = get_user_settings_service()
        success = service.delete_settings(user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete user settings")
        return {"success": True, "message": "User settings deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting user settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete user settings: {str(e)}")

