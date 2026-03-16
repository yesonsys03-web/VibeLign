"""User management API."""
from core.database import find_user_by_id, update_user


def get_user_profile(user_id):
    """Get a user's public profile."""
    user = find_user_by_id(user_id)
    if not user:
        return None
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "bio": user.get("bio", ""),
        "created_at": user.get("created_at", ""),
    }


def update_user_profile(user_id, name=None, bio=None):
    """Update a user's profile fields."""
    updates = {}
    if name is not None:
        updates["name"] = name
    if bio is not None:
        updates["bio"] = bio
    if not updates:
        return {"success": False, "reason": "Nothing to update"}
    return update_user(user_id, updates)
