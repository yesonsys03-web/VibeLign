"""Database access layer."""

_users_db = {}
_next_id = 1


def init_db():
    """Initialize the database."""
    global _users_db, _next_id
    _users_db = {}
    _next_id = 1


def create_user(name, email, password_hash):
    """Create a new user and return their ID."""
    global _next_id
    user_id = _next_id
    _next_id += 1
    _users_db[user_id] = {
        "id": user_id,
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "bio": "",
        "login_attempts": 0,
    }
    return user_id


def find_user_by_email(email):
    """Find a user by their email address."""
    for user in _users_db.values():
        if user["email"] == email:
            return user
    return None


def find_user_by_id(user_id):
    """Find a user by their ID."""
    return _users_db.get(user_id)


def update_user(user_id, updates):
    """Update user fields."""
    user = _users_db.get(user_id)
    if not user:
        return {"success": False, "reason": "User not found"}
    for key, value in updates.items():
        user[key] = value
    return {"success": True}


def update_login_attempts(email, count):
    """Update the login attempt counter for a user."""
    user = find_user_by_email(email)
    if user:
        user["login_attempts"] = count
