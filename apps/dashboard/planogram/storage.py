"""
AlwaysSmile Merchandise Storage Interface.

Defines the contract for storing and retrieving:
- Floor arrangements
- Fixture information
- Planograms

Concrete implementations can use Django ORM or another
storage backend in the future.
"""

from abc import ABC, abstractmethod


class MerchandiseStorage(ABC):
    """Abstract interface for merchandise storage."""

    @abstractmethod
    def get_floor(self, floor_id: str) -> dict | None:
        """Retrieve a floor arrangement."""
        raise NotImplementedError

    @abstractmethod
    def save_floor(
        self,
        floor_id: str,
        arrangement: dict,
    ) -> None:
        """Save a floor arrangement."""
        raise NotImplementedError

    @abstractmethod
    def delete_fixture(self, fixture_id: str) -> None:
        """Delete a fixture."""
        raise NotImplementedError

    @abstractmethod
    def clear_floor(self, floor_id: str) -> None:
        """Delete all fixtures belonging to a floor."""
        raise NotImplementedError

    @abstractmethod
    def get_planogram(
        self,
        fixture_id: str,
    ) -> dict | None:
        """Retrieve a fixture planogram."""
        raise NotImplementedError

    @abstractmethod
    def save_planogram(
        self,
        fixture_id: str,
        planogram: dict,
    ) -> None:
        """Save a fixture planogram."""
        raise NotImplementedError
