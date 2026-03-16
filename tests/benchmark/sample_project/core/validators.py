"""Input validation utilities."""
import re
from config import PASSWORD_MIN_LENGTH, ALLOWED_EMAIL_DOMAINS


def validate_email(email):
    """Check if the email format is valid."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_email_domain(email):
    """Check if the email domain is in the allowed list."""
    if not validate_email(email):
        return False
    domain = email.split("@")[1]
    return domain in ALLOWED_EMAIL_DOMAINS


def validate_password(password):
    """Check if the password meets minimum requirements."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_upper and has_lower and has_digit
