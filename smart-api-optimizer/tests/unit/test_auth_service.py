import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth import AuthService
from app.core.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.models import User

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
class TestAuthService:
    """Test authentication service."""

    async def test_register_user(self, db_session: AsyncSession):
        """Test user registration."""
        service = AuthService(db_session)
        
        user = await service.register_user(
            username="newuser",
            email="new@example.com",
            password="Password123!"
        )
        
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.is_active is True

    async def test_register_duplicate_username(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test registration with duplicate username."""
        service = AuthService(db_session)
        
        with pytest.raises(UserAlreadyExistsError):
            await service.register_user(
                username=test_user.username,
                email="different@example.com",
                password="Password123!"
            )

    async def test_authenticate_user_success(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test successful user authentication."""
        service = AuthService(db_session)
        
        user = await service.authenticate_user(
            username="testuser",
            password="TestPassword123!"
        )
        
        assert user is not None
        assert user.username == "testuser"
        assert user.id == test_user.id

    async def test_authenticate_user_wrong_password(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test authentication with wrong password."""
        service = AuthService(db_session)
        
        user = await service.authenticate_user(
            username="testuser",
            password="WrongPassword123!"
        )
        
        assert user is None

    async def test_authenticate_user_not_found(
        self, db_session: AsyncSession
    ):
        """Test authentication with non-existent user."""
        service = AuthService(db_session)
        
        user = await service.authenticate_user(
            username="nonexistent",
            password="Password123!"
        )
        
        assert user is None

    async def test_create_tokens(self, db_session: AsyncSession, test_user: User):
        """Test token creation for user."""
        service = AuthService(db_session)
        
        tokens = await service.create_tokens(test_user.id)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

    async def test_refresh_access_token(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test access token refresh."""
        service = AuthService(db_session)
        
        tokens = await service.create_tokens(test_user.id)
        refresh_token = tokens["refresh_token"]
        
        new_tokens = await service.refresh_access_token(refresh_token)
        
        assert new_tokens is not None
        assert "access_token" in new_tokens
        assert new_tokens["access_token"] != tokens["access_token"]

    async def test_get_user(self, db_session: AsyncSession, test_user: User):
        """Test getting user by ID."""
        service = AuthService(db_session)
        
        user = await service.get_user(test_user.id)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.username == "testuser"

    async def test_get_user_not_found(self, db_session: AsyncSession):
        """Test getting non-existent user."""
        service = AuthService(db_session)
        
        user = await service.get_user(99999)
        
        assert user is None
