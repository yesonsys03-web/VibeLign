"""User profile page."""
from api.users import get_user_profile, update_user_profile


def render_profile(user_id):
    """Display user profile page."""
    profile = get_user_profile(user_id)
    if not profile:
        return {"error": "User not found", "status": 404}
    return {
        "title": f"Profile - {profile['name']}",
        "user": profile,
        "editable_fields": ["name", "bio"],
    }


def handle_profile_update(user_id, name, bio):
    """Process profile edit form."""
    if not name:
        return {"error": "Name is required", "status": 400}
    result = update_user_profile(user_id, name=name, bio=bio)
    if result["success"]:
        return {"message": "Profile updated", "status": 200}
    return {"error": "Update failed", "status": 500}
