#!/usr/bin/env python3
"""
Initialize the database and create an admin user
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import init_db, AsyncSessionLocal
from app.models import User
from app.auth import get_password_hash


async def create_admin_user():
    """Create the default admin user"""
    async with AsyncSessionLocal() as session:
        # Check if admin already exists
        result = await session.execute(select(User).where(User.username == "admin"))
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print("Admin user already exists")
            return

        # Create admin user
        admin = User(
            username="admin",
            email="admin@example.com",
            full_name="Administrator",
            hashed_password=get_password_hash("admin"),
            is_active=True,
            is_superuser=True
        )

        session.add(admin)
        await session.commit()
        print("Admin user created successfully")
        print("Username: admin")
        print("Password: admin")
        print("\nWARNING: Please change the admin password immediately!")


async def main():
    """Main initialization function"""
    print("Initializing database...")
    await init_db()
    print("Database initialized")

    print("\nCreating admin user...")
    await create_admin_user()
    print("\nInitialization complete!")


if __name__ == "__main__":
    asyncio.run(main())
