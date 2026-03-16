"""Simple web app entry point."""
from api.auth import login_user, register_user
from api.users import get_user_profile
from core.database import init_db


def main():
    init_db()
    print("Server started on port 8000")


if __name__ == "__main__":
    main()
