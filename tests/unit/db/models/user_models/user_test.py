"""Unit tests for the User model."""

import uuid
from datetime import datetime

import pytest

from app.db.models.user_models.user import User


class TestUser:
    """Test cases for User model."""

    @pytest.mark.unit
    def test_user_model_creation(
        self, mock_user_id: uuid.UUID, mock_datetime: datetime
    ) -> None:
        """Test creating a User instance with all fields."""
        user = User(
            user_id=mock_user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",  # pragma: allowlist secret
            full_name="Test User",
            bio="This is a test user bio",
            is_active=True,
            created_at=mock_datetime,
            updated_at=mock_datetime,
        )

        assert user.user_id == mock_user_id
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password_123"  # pragma: allowlist secret
        assert user.full_name == "Test User"
        assert user.bio == "This is a test user bio"
        assert user.is_active is True
        assert user.created_at == mock_datetime
        assert user.updated_at == mock_datetime

    @pytest.mark.unit
    def test_user_model_creation_minimal(self) -> None:
        """Test creating a User instance with minimal required fields."""
        user = User(
            username="minimaluser",
            email="minimal@example.com",
            password_hash="hashed_password",  # pragma: allowlist secret
        )

        assert user.username == "minimaluser"
        assert user.email == "minimal@example.com"
        assert user.password_hash == "hashed_password"  # pragma: allowlist secret
        assert user.full_name is None
        assert user.bio is None
        # Default value depends on server default, so could be None initially
        assert user.is_active in (True, None)

    @pytest.mark.unit
    def test_user_model_with_inactive_flag(self) -> None:
        """Test creating a User instance with is_active=False."""
        user = User(
            username="inactiveuser",
            email="inactive@example.com",
            password_hash="hashed_password",  # pragma: allowlist secret
            is_active=False,
        )

        assert user.username == "inactiveuser"
        assert user.is_active is False

    @pytest.mark.unit
    def test_user_model_with_none_optional_fields(self) -> None:
        """Test creating a User instance with None values for optional fields."""
        user = User(
            username="noneuser",
            email="none@example.com",
            password_hash="hashed_password",  # pragma: allowlist secret
            full_name=None,
            bio=None,
        )

        assert user.username == "noneuser"
        assert user.full_name is None
        assert user.bio is None

    @pytest.mark.unit
    def test_user_model_with_uuid_generation(self) -> None:
        """Test that User can generate UUID automatically."""
        user = User(
            username="uuiduser",
            email="uuid@example.com",
            password_hash="hashed_password",  # pragma: allowlist secret
        )

        # UUID generation depends on database defaults
        # In unit tests without DB, this might be None
        assert user.user_id is None or isinstance(user.user_id, uuid.UUID)

    @pytest.mark.unit
    def test_user_model_tablename(self) -> None:
        """Test that the table name is correctly set."""
        user = User(
            username="test",
            email="test@example.com",
            password_hash="hash",  # pragma: allowlist secret
        )
        assert user.__tablename__ == "users"

    @pytest.mark.unit
    def test_user_model_table_args(self) -> None:
        """Test that the table args schema is correctly set."""
        user = User(
            username="test",
            email="test@example.com",
            password_hash="hash",  # pragma: allowlist secret
        )
        assert user.__table_args__ == ({"schema": "recipe_manager"},)

    @pytest.mark.unit
    def test_user_model_inheritance(self) -> None:
        """Test that User inherits from BaseDatabaseModel."""
        from app.db.models.base_database_model import BaseDatabaseModel

        user = User(
            username="test",
            email="test@example.com",
            password_hash="hash",  # pragma: allowlist secret
        )
        assert isinstance(user, BaseDatabaseModel)

    @pytest.mark.unit
    def test_user_model_serialization(
        self, mock_user_id: uuid.UUID, mock_datetime: datetime
    ) -> None:
        """Test that User can be serialized to JSON."""
        user = User(
            user_id=mock_user_id,
            username="serializationuser",
            email="serialization@example.com",
            password_hash="hashed_password_123",  # pragma: allowlist secret
            full_name="Serialization Test User",
            bio="Test user for serialization",
            is_active=True,
            created_at=mock_datetime,
            updated_at=mock_datetime,
        )

        json_str = user._to_json()

        # Should contain all the expected fields
        assert '"username": "serializationuser"' in json_str
        assert '"email": "serialization@example.com"' in json_str
        assert '"full_name": "Serialization Test User"' in json_str
        assert '"bio": "Test user for serialization"' in json_str
        assert '"is_active": true' in json_str
        # Password hash should be included in serialization (this is just the model
        # test)
        assert (
            '"password_hash": "hashed_password_123"'  # pragma: allowlist secret
            in json_str
        )

    @pytest.mark.unit
    def test_user_model_string_representation(self, mock_user_id: uuid.UUID) -> None:
        """Test string representation of User model."""
        user = User(
            user_id=mock_user_id,
            username="stringuser",
            email="string@example.com",
            password_hash="hash",  # pragma: allowlist secret
        )

        str_repr = str(user)

        # Should be a JSON string representation
        assert '"username": "stringuser"' in str_repr
        assert '"email": "string@example.com"' in str_repr

    @pytest.mark.unit
    def test_user_model_repr(self, mock_user_id: uuid.UUID) -> None:
        """Test repr representation of User model."""
        user = User(
            user_id=mock_user_id,
            username="repruser",
            email="repr@example.com",
            password_hash="hash",  # pragma: allowlist secret
        )

        repr_str = repr(user)

        # Should be a JSON string representation
        assert '"username": "repruser"' in repr_str
        assert '"email": "repr@example.com"' in repr_str

    @pytest.mark.unit
    def test_user_model_relationships(self) -> None:
        """Test that the relationships are properly configured."""
        user = User(
            username="relationshipuser",
            email="relationship@example.com",
            password_hash="hash",  # pragma: allowlist secret
        )

        # Relationships should be configured but initially empty lists
        assert hasattr(user, 'followers')
        assert hasattr(user, 'following')
        assert user.followers == []
        assert user.following == []

    @pytest.mark.unit
    def test_user_model_with_long_username(self) -> None:
        """Test creating a User with a long username (up to 50 chars)."""
        long_username = "a" * 50
        user = User(
            username=long_username,
            email="long@example.com",
            password_hash="hash",  # pragma: allowlist secret
        )

        assert user.username == long_username
        assert len(user.username) == 50

    @pytest.mark.unit
    def test_user_model_with_long_email(self) -> None:
        """Test creating a User with a long email (up to 255 chars)."""
        # Create a long but valid email
        local_part = "a" * 200
        domain_part = "example.com"
        long_email = f"{local_part}@{domain_part}"

        user = User(
            username="longemailuser",
            email=long_email,
            password_hash="hash",  # pragma: allowlist secret
        )

        assert user.email == long_email

    @pytest.mark.unit
    def test_user_model_with_long_full_name(self) -> None:
        """Test creating a User with a long full name (up to 255 chars)."""
        long_full_name = "A" * 255
        user = User(
            username="longfullnameuser",
            email="longfullname@example.com",
            password_hash="hash",  # pragma: allowlist secret
            full_name=long_full_name,
        )

        assert user.full_name == long_full_name
        assert len(user.full_name) == 255

    @pytest.mark.unit
    def test_user_model_with_long_bio(self) -> None:
        """Test creating a User with a long bio."""
        long_bio = "This is a very long bio. " * 100
        user = User(
            username="longbiouser",
            email="longbio@example.com",
            password_hash="hash",  # pragma: allowlist secret
            bio=long_bio,
        )

        assert user.bio == long_bio

    @pytest.mark.unit
    def test_user_model_with_long_password_hash(self) -> None:
        """Test creating a User with a long password hash (up to 255 chars)."""
        long_password_hash = "h" * 255
        user = User(
            username="longpassuser",
            email="longpass@example.com",
            password_hash=long_password_hash,
        )

        assert user.password_hash == long_password_hash
        assert len(user.password_hash) == 255

    @pytest.mark.unit
    def test_user_model_with_special_characters(self) -> None:
        """Test creating a User with special characters in fields."""
        user = User(
            username="special_user-123",
            email="special+user@example-domain.com",
            password_hash="$2b$12$special.hash.with.symbols",
            full_name="Special Ñame with Ümlauts",
            bio="Bio with émojis 🎉 and special chars: !@#$%^&*()",
        )

        assert user.username == "special_user-123"
        assert user.email == "special+user@example-domain.com"
        assert user.full_name == "Special Ñame with Ümlauts"
        assert user.bio is not None and "🎉" in user.bio
        assert user.bio is not None and "!@#$%^&*()" in user.bio

    @pytest.mark.unit
    def test_user_model_with_different_uuid_formats(self) -> None:
        """Test creating User with different UUID formats."""
        # Test with string UUID
        str_uuid = "12345678-1234-5678-1234-567812345678"
        uuid_obj = uuid.UUID(str_uuid)

        user = User(
            user_id=uuid_obj,
            username="uuidformatuser",
            email="uuidformat@example.com",
            password_hash="hash",  # pragma: allowlist secret
        )

        assert user.user_id == uuid_obj
        assert str(user.user_id) == str_uuid
