"""
CLI commands for database management
"""
import asyncio
import click


@click.group()
def cli():
    """Database management commands."""
    pass


@cli.command()
def init():
    """Initialize database with tables and seed data."""
    import asyncio
    from app.db.init_db import main

    asyncio.run(main())


@cli.command()
def create_user():
    """Create a new user interactively."""
    import asyncio
    import getpass
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.core.database import engine
    from app.core.security import hash_password
    from app.models.user import User
    from uuid import uuid4

    email = input("Email: ")
    full_name = input("Full Name: ")
    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm Password: ")

    if password != confirm_password:
        click.echo("Passwords do not match!")
        return

    async def create():
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            # Check if user exists
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.email == email)
            )
            if result.scalar_one_or_none():
                click.echo(f"User with email {email} already exists!")
                return

            # Create user
            user = User(
                id=str(uuid4()),
                email=email,
                hashed_password=hash_password(password),
                full_name=full_name,
                is_active=True,
            )

            session.add(user)
            await session.commit()
            click.echo(f"✓ User {email} created successfully!")

    asyncio.run(create())


@cli.command()
@click.option("--email", prompt=True, help="User email")
def reset_password(email: str):
    """Reset user password."""
    import asyncio
    import getpass
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.core.database import engine
    from app.core.security import hash_password
    from sqlalchemy import select
    from app.models.user import User

    password = getpass.getpass("New Password: ")

    async def reset():
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()

            if not user:
                click.echo(f"User with email {email} not found!")
                return

            user.hashed_password = hash_password(password)
            await session.commit()
            click.echo(f"✓ Password reset for {email}")

    asyncio.run(reset())


if __name__ == "__main__":
    cli()
