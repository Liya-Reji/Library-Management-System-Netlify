"""
Safe Administrator Verification and Recovery Script.
Usage:
  1. Check existing administrator accounts (read-only):
       python scripts/create_admin.py --check
  2. Interactively create a new administrator (if none exists):
       python scripts/create_admin.py
"""
import os
import sys
import getpass
from urllib.parse import urlparse

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from app import create_app
from models import db, User

def mask_connection_url(url):
    if not url:
        return "None"
    try:
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(f":{parsed.password}@", ":****@")
            return parsed._replace(netloc=netloc).geturl()
    except Exception:
        pass
    return "Configured Database URL"

def main():
    check_only = "--check" in sys.argv or "-c" in sys.argv
    app = create_app()

    with app.app_context():
        # Ensure tables exist
        db.create_all()

        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        masked_uri = mask_connection_url(db_uri)
        print(f"[*] Target Database: {masked_uri}")

        existing_admins = User.query.filter_by(role="admin").all()

        if check_only:
            print("\n=== Administrator Account Verification ===")
            if existing_admins:
                print(f"[+] Found {len(existing_admins)} existing administrator account(s):")
                for a in existing_admins:
                    created_str = a.created_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(a, "created_at", None) else "N/A"
                    print(f"    - Username: {a.username} | Email: {a.email} | Created: {created_str}")
                print("[*] Your administrator account exists. No modifications needed.")
            else:
                print("[-] No administrator accounts found in this database.")
                print("[*] Run `python scripts/create_admin.py` to create one.")
            return

        if existing_admins:
            print(f"\n[*] Notice: Found {len(existing_admins)} existing administrator account(s):")
            for a in existing_admins:
                print(f"    - Username: {a.username} | Email: {a.email}")
            print("\nTo protect account integrity, existing administrators are never overwritten.")
            choice = input("Do you still want to create an ADDITIONAL administrator? (y/N): ").strip().lower()
            if choice not in ("y", "yes"):
                print("Exiting without making changes.")
                return

        print("\n=== Create Administrator Account ===")
        # Support environment variables for automation, or prompt interactively
        username = os.getenv("NEW_ADMIN_USERNAME") or input("Admin username: ").strip()
        email = (os.getenv("NEW_ADMIN_EMAIL") or input("Admin email: ")).strip().lower()

        if not username or not email:
            print("[!] Error: Username and email cannot be blank.")
            return

        # Check for conflicts
        if User.query.filter((User.username == username) | (User.email == email)).first():
            print(f"[!] Error: A user with username '{username}' or email '{email}' already exists.")
            return

        if os.getenv("NEW_ADMIN_PASSWORD"):
            password = os.getenv("NEW_ADMIN_PASSWORD")
        else:
            password = getpass.getpass("Enter strong password (min 8 chars): ")
            confirm_pwd = getpass.getpass("Confirm password: ")
            if password != confirm_pwd:
                print("[!] Error: Passwords do not match.")
                return

        if len(password) < 8:
            print("[!] Error: Password must be at least 8 characters long.")
            return

        admin = User(
            username=username,
            email=email,
            role="admin"
        )
        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()

        print(f"[+] Success: Administrator account '{username}' created successfully.")

if __name__ == "__main__":
    main()
