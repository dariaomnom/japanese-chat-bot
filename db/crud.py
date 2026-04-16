from .base import AsyncSessionLocal
from .models import User
from sqlalchemy import select


async def get_user_by_telegram_id(telegram_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def create_user(telegram_id: int):
    async with AsyncSessionLocal() as session:
        user = User(telegram_id=telegram_id)

        session.add(user)
        await session.commit()

        return user


async def get_or_create_user(telegram_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            return user, False

        user = User(telegram_id=telegram_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user, True


async def set_user_words_limit(telegram_id: int, limit: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.words_per_day = limit
            await session.commit()
            return True
    return False
