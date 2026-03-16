"""Application configuration."""

DATABASE_URL = "sqlite:///app.db"
SECRET_KEY = "change-me-in-production"
TOKEN_EXPIRY_HOURS = 24
MAX_LOGIN_ATTEMPTS = 5
PASSWORD_MIN_LENGTH = 8
ALLOWED_EMAIL_DOMAINS = ["gmail.com", "naver.com", "kakao.com"]
