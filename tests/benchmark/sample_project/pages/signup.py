"""Signup page UI logic."""
from api.auth import register_user
from core.validators import validate_email, validate_password


def render_signup_form():
    """Display the signup form."""
    return {
        "title": "Create Account",
        "fields": [
            {"name": "name", "type": "text", "placeholder": "Your name"},
            {"name": "email", "type": "email", "placeholder": "Email address"},
            {"name": "password", "type": "password", "placeholder": "Password"},
            {"name": "password_confirm", "type": "password", "placeholder": "Confirm password"},
        ],
        "submit_label": "Create Account",
    }


def handle_signup(name, email, password, password_confirm):
    """Process signup form submission."""
    if not all([name, email, password, password_confirm]):
        return {"error": "All fields are required", "status": 400}

    if password != password_confirm:
        return {"error": "Passwords do not match", "status": 400}

    if not validate_email(email):
        return {"error": "Invalid email format", "status": 400}

    if not validate_password(password):
        return {"error": "Password too weak", "status": 400}

    result = register_user(name, email, password)
    if result["success"]:
        return {"message": "Account created successfully", "status": 201}
    else:
        return {"error": result.get("reason", "Registration failed"), "status": 409}
