"""Business logic for accounts and token lifecycle."""
import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from esone_api.models import RefreshToken, Role, User
from esone_api.schemas import TokenResponse, UserCreate
from esone_api.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)


async def register_user(session: AsyncSession, data: UserCreate) -> User:
    taken = await session.scalar(
        select(User.id).where(
            (func.lower(User.username) == data.username.lower())
            | (func.lower(User.email) == data.email.lower())
        )
    )
    if taken is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Username or email already in use")

    user = User(
        username=data.username,
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        role=Role.VIEWER.value,  # never trust a client-supplied role
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate(session: AsyncSession, username: str, password: str) -> User:
    user = await session.scalar(
        select(User).where(func.lower(User.username) == username.strip().lower())
    )
    # Verify even when the user is missing so timing does not leak existence.
    ok = verify_password(password, user.hashed_password if user else "$2b$12$invalidinvalidinvalidinvalidinvalidinvalidinvalidinvali")
    if user is None or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return user


async def issue_tokens(session: AsyncSession, user: User) -> TokenResponse:
    access, expires_in = create_access_token(user.id, user.role)
    refresh, jti, expires_at = create_refresh_token(user.id, user.role)
    session.add(RefreshToken(jti=jti, user_id=user.id, expires_at=expires_at))
    await session.commit()
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=expires_in)


async def revoke_all_for_user(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )


async def rotate_refresh_token(session: AsyncSession, token: str) -> TokenResponse:
    try:
        payload = decode_token(token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    record = await session.scalar(select(RefreshToken).where(RefreshToken.jti == payload["jti"]))
    if record is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Unknown refresh token")

    if record.revoked:
        # Reuse of a rotated token: assume theft and cut every session for the user.
        logger.warning("refresh token reuse detected for user_id=%s", record.user_id)
        await revoke_all_for_user(session, record.user_id)
        await session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")

    if record.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")

    user = await session.get(User, record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    record.revoked = True
    return await issue_tokens(session, user)


async def logout(session: AsyncSession, token: str) -> None:
    """Revoke one refresh token. Idempotent: unknown or bad tokens are ignored."""
    try:
        payload = decode_token(token, expected_type="refresh")
    except TokenError:
        return
    await session.execute(
        update(RefreshToken).where(RefreshToken.jti == payload["jti"]).values(revoked=True)
    )
    await session.commit()


async def change_password(
    session: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if current_password == new_password:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="New password must differ from the current one"
        )
    user.hashed_password = hash_password(new_password)
    await revoke_all_for_user(session, user.id)
    await session.commit()


async def list_users(session: AsyncSession, limit: int, offset: int) -> tuple[list[User], int]:
    total = await session.scalar(select(func.count(User.id))) or 0
    rows = await session.scalars(
        select(User).order_by(User.created_at.desc(), User.id.desc()).limit(limit).offset(offset)
    )
    return list(rows), total


async def admin_update_user(
    session: AsyncSession,
    actor: User,
    user_id: int,
    role: Role | None,
    is_active: bool | None,
) -> User:
    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == actor.id and (
        (role is not None and role != Role.ADMIN) or is_active is False
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="You cannot demote or deactivate yourself"
        )

    if role is not None:
        target.role = role.value
    if is_active is not None:
        target.is_active = is_active
        if not is_active:
            await revoke_all_for_user(session, target.id)
    await session.commit()
    await session.refresh(target)
    return target


async def ensure_admin(session: AsyncSession, username: str, email: str, password: str) -> None:
    """Create the configured first administrator if that username is free."""
    exists = await session.scalar(select(User.id).where(User.username == username))
    if exists is not None:
        return
    session.add(
        User(
            username=username,
            email=email.lower(),
            hashed_password=hash_password(password),
            role=Role.ADMIN.value,
        )
    )
    await session.commit()
    logger.info("seeded administrator account %r", username)
