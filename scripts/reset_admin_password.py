"""Development/on-premise administrator recovery tool.

Run this inside the API container. Password input is hidden and is never
passed as a command-line argument.
"""
import argparse
import getpass
import sys
from pathlib import Path

# Executing this file directly makes Python start in /app/scripts. Add the
# project root so imports such as app.core.database remain available.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="List users or reset an administrator password.")
    parser.add_argument("--list", action="store_true", help="List active companies and users.")
    parser.add_argument("--company-slug")
    parser.add_argument("--email")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.list:
            rows = db.execute(text("""
                SELECT c.slug,u.email,u.role::text,u.is_active
                FROM users u JOIN companies c ON c.id=u.company_id
                ORDER BY c.slug,u.email
            """)).mappings()
            for row in rows:
                print(f"company={row['slug']}  email={row['email']}  role={row['role']}  active={row['is_active']}")
            return
        if not args.company_slug or not args.email:
            parser.error("use --list, or provide --company-slug and --email")
        password = getpass.getpass("New password (at least 12 characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            parser.error("passwords do not match")
        if len(password) < 12:
            parser.error("password must contain at least 12 characters")
        result = db.execute(text("""
            UPDATE users u SET password_hash=:password_hash, is_active=true
            FROM companies c WHERE u.company_id=c.id AND c.slug=:company_slug AND u.email=:email
            RETURNING u.id
        """), {"password_hash": hash_password(password), "company_slug": args.company_slug, "email": args.email.lower()})
        if result.scalar_one_or_none() is None:
            parser.error("no user found for that company slug and email")
        db.commit()
        print("Password reset completed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
