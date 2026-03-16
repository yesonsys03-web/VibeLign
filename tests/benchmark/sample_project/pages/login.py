"""Login page UI logic."""
from api.auth import login_user
from core.validators import validate_email


def render_login_form():
    """Display the login form with email and password fields."""
    return {
        "title": "Login",
        "fields": [
            {"name": "email", "type": "email", "placeholder": "Enter your email"},
            {"name": "password", "type": "password", "placeholder": "Enter your password"},
        ],
        "submit_label": "Sign In",
    }


def handle_login(email, password):
    """Process login form submission."""
    if not email or not password:
        return {"error": "All fields are required", "status": 400}

    if not validate_email(email):
        return {"error": "Invalid email format", "status": 400}

    result = login_user(email, password)
    if result["success"]:
        return {"message": "Login successful", "token": result["token"], "status": 200}
    else:
        return {"error": "Invalid email or password", "status": 401}


def render_login_error(error_message):
    """Display error message on the login page."""
    return {"alert_type": "danger", "message": error_message}
