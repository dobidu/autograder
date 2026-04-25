#!/usr/bin/env python3
"""Create a professor (admin) account."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Base, engine
from app.models import User
from app.security import hash_password

Base.metadata.create_all(bind=engine)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Create a professor account")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    existing = db.query(User).filter(User.email == args.email).first()
    if existing:
        print(f"User with email {args.email} already exists.")
        sys.exit(1)

    user = User(
        name=args.name,
        email=args.email,
        password_hash=hash_password(args.password),
        role="professor",
    )
    db.add(user)
    db.commit()
    print(f"Professor '{args.name}' created successfully (id={user.id}).")
    db.close()


if __name__ == "__main__":
    main()
