"""Authentication API."""
import hashlib
from core.database import find_user_by_email, create_user, update_login_attempts
from config import SECRET_KEY, MAX_LOGIN_ATTEMPTS, TOKEN_EXPIRY_HOURS


def _hash_password(password):
    """Hash a password with the secret key."""
    return hashlib.sha256(f"{password}{SECRET_KEY}".encode()).hexdigest()


def _generate_token(user_id):
    """Generate an auth token for the user."""
    import time
    payload = f"{user_id}:{time.time()}"
    return hashlib.sha256(f"{payload}{SECRET_KEY}".encode()).hexdigest()


def login_user(email, password):
    """Authenticate a user with email and password."""
    user = find_user_by_email(email)
    if not user:
        return {"success": False, "reason": "User not found"}

    if user.get("login_attempts", 0) >= MAX_LOGIN_ATTEMPTS:
        return {"success": False, "reason": "Account locked"}

    if user["password_hash"] != _hash_password(password):
        update_login_attempts(email, user.get("login_attempts", 0) + 1)
        return {"success": False, "reason": "Wrong password"}

    update_login_attempts(email, 0)
    token = _generate_token(user["id"])
    return {"success": True, "token": token, "user_id": user["id"]}


def register_user(name, email, password):
    """Register a new user."""
    existing = find_user_by_email(email)
    if existing:
        return {"success": False, "reason": "Email already registered"}

    password_hash = _hash_password(password)
    user_id = create_user(name, email, password_hash)
    return {"success": True, "user_id": user_id}
