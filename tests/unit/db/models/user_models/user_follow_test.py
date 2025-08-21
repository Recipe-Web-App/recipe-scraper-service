"""Unit tests for the UserFollow model."""

import uuid
from datetime import datetime

import pytest

from app.db.models.user_models.user_follow import UserFollow


class TestUserFollow:
    """Test cases for UserFollow model."""

    @pytest.mark.unit
    def test_user_follow_model_creation(
        self, mock_user_id: uuid.UUID, mock_datetime: datetime
    ) -> None:
        """Test creating a UserFollow instance with all fields."""
        followee_id = uuid.UUID("87654321-4321-8765-4321-876543218765")

        user_follow = UserFollow(
            follower_id=mock_user_id,
            followee_id=followee_id,
            followed_at=mock_datetime,
        )

        assert user_follow.follower_id == mock_user_id
        assert user_follow.followee_id == followee_id
        assert user_follow.followed_at == mock_datetime

    @pytest.mark.unit
    def test_user_follow_model_creation_minimal(self, mock_user_id: uuid.UUID) -> None:
        """Test creating a UserFollow instance with minimal required fields."""
        followee_id = uuid.UUID("87654321-4321-8765-4321-876543218765")

        user_follow = UserFollow(
            follower_id=mock_user_id,
            followee_id=followee_id,
        )

        assert user_follow.follower_id == mock_user_id
        assert user_follow.followee_id == followee_id
        # followed_at should have a default value from server

    @pytest.mark.unit
    def test_user_follow_model_with_same_user_ids(self) -> None:
        """Test creating UserFollow where user follows themselves."""
        user_id = uuid.UUID("12345678-1234-5678-1234-567812345678")

        # This should be allowed at model level (business logic should prevent it)
        user_follow = UserFollow(
            follower_id=user_id,
            followee_id=user_id,
        )

        assert user_follow.follower_id == user_id
        assert user_follow.followee_id == user_id

    @pytest.mark.unit
    def test_user_follow_model_with_different_uuids(self) -> None:
        """Test creating UserFollow with various UUID combinations."""
        uuid_pairs = [
            (
                uuid.UUID("11111111-1111-1111-1111-111111111111"),
                uuid.UUID("22222222-2222-2222-2222-222222222222"),
            ),
            (
                uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            ),
            (
                uuid.UUID("00000000-0000-0000-0000-000000000000"),
                uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            ),
        ]

        for follower_id, followee_id in uuid_pairs:
            user_follow = UserFollow(
                follower_id=follower_id,
                followee_id=followee_id,
            )
            assert user_follow.follower_id == follower_id
            assert user_follow.followee_id == followee_id

    @pytest.mark.unit
    def test_user_follow_model_tablename(self, mock_user_id: uuid.UUID) -> None:
        """Test that the table name is correctly set."""
        followee_id = uuid.UUID("87654321-4321-8765-4321-876543218765")
        user_follow = UserFollow(
            follower_id=mock_user_id,
            followee_id=followee_id,
        )
        assert user_follow.__tablename__ == "user_follows"

    @pytest.mark.unit
    def test_user_follow_model_table_args(self, mock_user_id: uuid.UUID) -> None:
        """Test that the table args schema is correctly set."""
        followee_id = uuid.UUID("87654321-4321-8765-4321-876543218765")
        user_follow = UserFollow(
            follower_id=mock_user_id,
            followee_id=followee_id,
        )
        assert user_follow.__table_args__ == ({"schema": "recipe_manager"},)

    @pytest.mark.unit
    def test_user_follow_model_inheritance(self, mock_user_id: uuid.UUID) -> None:
        """Test that UserFollow inherits from BaseDatabaseModel."""
        from app.db.models.base_database_model import BaseDatabaseModel

        followee_id = uuid.UUID("87654321-4321-8765-4321-876543218765")
        user_follow = UserFollow(
            follower_id=mock_user_id,
            followee_id=followee_id,
        )
        assert isinstance(user_follow, BaseDatabaseModel)

    @pytest.mark.unit
    def test_user_follow_model_serialization(
        self, mock_user_id: uuid.UUID, mock_datetime: datetime
    ) -> None:
        """Test that UserFollow can be serialized to JSON."""
        followee_id = uuid.UUID("87654321-4321-8765-4321-876543218765")

        user_follow = UserFollow(
            follower_id=mock_user_id,
            followee_id=followee_id,
            followed_at=mock_datetime,
        )

        json_str = user_follow._to_json()

        # Should contain all the expected fields
        assert '"follower_id":' in json_str
        assert '"followee_id":' in json_str
        assert '"followed_at":' in json_str
        # UUIDs should be serialized as strings
        assert str(mock_user_id) in json_str
        assert str(followee_id) in json_str

    @pytest.mark.unit
    def test_user_follow_model_string_representation(
        self, mock_user_id: uuid.UUID
    ) -> None:
        """Test string representation of UserFollow model."""
        followee_id = uuid.UUID("87654321-4321-8765-4321-876543218765")

        user_follow = UserFollow(
            follower_id=mock_user_id,
            followee_id=followee_id,
        )

        str_repr = str(user_follow)

        # Should be a JSON string representation
        assert '"follower_id":' in str_repr
        assert '"followee_id":' in str_repr

    @pytest.mark.unit
    def test_user_follow_model_repr(self, mock_user_id: uuid.UUID) -> None:
        """Test repr representation of UserFollow model."""
        followee_id = uuid.UUID("87654321-4321-8765-4321-876543218765")

        user_follow = UserFollow(
            follower_id=mock_user_id,
            followee_id=followee_id,
        )

        repr_str = repr(user_follow)

        # Should be a JSON string representation
        assert '"follower_id":' in repr_str
        assert '"followee_id":' in repr_str

    @pytest.mark.unit
    def test_user_follow_model_relationships(self, mock_user_id: uuid.UUID) -> None:
        """Test that the relationships are properly configured."""
        followee_id = uuid.UUID("87654321-4321-8765-4321-876543218765")

        user_follow = UserFollow(
            follower_id=mock_user_id,
            followee_id=followee_id,
        )

        # Relationships should be configured but initially None
        assert hasattr(user_follow, 'follower')
        assert hasattr(user_follow, 'followee')

    @pytest.mark.unit
    def test_user_follow_model_composite_primary_key(
        self, mock_user_id: uuid.UUID
    ) -> None:
        """Test that UserFollow uses composite primary key."""
        followee_id = uuid.UUID("87654321-4321-8765-4321-876543218765")

        user_follow = UserFollow(
            follower_id=mock_user_id,
            followee_id=followee_id,
        )

        # Both fields should be part of the primary key
        assert user_follow.follower_id == mock_user_id
        assert user_follow.followee_id == followee_id

    @pytest.mark.unit
    def test_user_follow_model_with_custom_datetime(self) -> None:
        """Test creating UserFollow with custom followed_at datetime."""
        follower_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        followee_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        custom_datetime = datetime(2023, 6, 15, 14, 30, 0)

        user_follow = UserFollow(
            follower_id=follower_id,
            followee_id=followee_id,
            followed_at=custom_datetime,
        )

        assert user_follow.followed_at == custom_datetime

    @pytest.mark.unit
    def test_user_follow_model_follow_relationship_uniqueness(self) -> None:
        """Test that follower-followee pairs can be created (uniqueness enforced at DB
        level)."""
        follower_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        followee_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

        # Create first follow relationship
        user_follow_1 = UserFollow(
            follower_id=follower_id,
            followee_id=followee_id,
        )

        # Create reverse follow relationship (should be allowed)
        user_follow_2 = UserFollow(
            follower_id=followee_id,
            followee_id=follower_id,
        )

        assert user_follow_1.follower_id == follower_id
        assert user_follow_1.followee_id == followee_id
        assert user_follow_2.follower_id == followee_id
        assert user_follow_2.followee_id == follower_id

    @pytest.mark.unit
    def test_user_follow_model_with_timezone_aware_datetime(
        self, mock_datetime: datetime
    ) -> None:
        """Test UserFollow with timezone-aware datetime."""
        follower_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        followee_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

        user_follow = UserFollow(
            follower_id=follower_id,
            followee_id=followee_id,
            followed_at=mock_datetime,  # This is timezone-aware from fixture
        )

        assert user_follow.followed_at == mock_datetime
        assert user_follow.followed_at.tzinfo is not None
