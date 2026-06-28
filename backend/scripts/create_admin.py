"""Script to create a system administrator user in PregAI."""
import argparse
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.database import crud, database
from backend.api.routes.auth import get_password_hash


def create_admin(username, email, password):
    db = next(database.get_db())
    try:
        # Check if user already exists
        db_user = crud.get_user_by_username(db, username=username)
        if db_user:
            print(f"User '{username}' already exists. Updating role to system_admin...")
            db_user.role = 'system_admin'
            db.commit()
            print("Role updated successfully.")
            return

        db_user = crud.get_user_by_email(db, email=email)
        if db_user:
            print(f"User with email '{email}' already exists.")
            return

        hashed_password = get_password_hash(password)
        new_admin = crud.create_user(
            db=db,
            username=username,
            email=email,
            password_hash=hashed_password,
            role='system_admin'
        )
        print(f"Admin user '{username}' created successfully with user_id: {new_admin.user_id}")
    except Exception as e:
        print(f"Error creating admin: {e}")
    finally:
        db.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Create or promote a PregAI system administrator.")
    parser.add_argument("--username", default="admin", help="Admin username.")
    parser.add_argument("--email", default="admin@pregai.com", help="Admin email address.")
    parser.add_argument(
        "--password",
        default=os.getenv("PREGAI_ADMIN_PASSWORD"),
        help="Admin password. Defaults to PREGAI_ADMIN_PASSWORD when omitted.",
    )
    args = parser.parse_args()

    if not args.password:
        parser.error("admin password is required via --password or PREGAI_ADMIN_PASSWORD")

    return args


if __name__ == "__main__":
    args = parse_args()
    create_admin(args.username, args.email, args.password)
