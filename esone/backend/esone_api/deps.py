"""FastAPI dependencies: current user and role guards."""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from esone_api.database import get_session
from esone_api.models import Role, User
from esone_api.security import TokenError, decode_token

bearer = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except TokenError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await session.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role):
    allowed = {r.value for r in roles}

    async def _guard(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail="You do not have permission to do that"
            )
        return user

    return _guard


AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]
