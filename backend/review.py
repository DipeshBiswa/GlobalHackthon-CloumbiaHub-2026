"""Review data models used by the translation pipeline."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Review:
    """A tour review written in English."""

    rating: float
    language: str
    date: date
    favorite: str
    improvement: str

    def __post_init__(self) -> None:
        if isinstance(self.rating, bool) or not isinstance(self.rating, (int, float)):
            raise TypeError("rating must be a number between 1 and 5.")
        if not 1 <= self.rating <= 5:
            raise ValueError("rating must be between 1 and 5.")
        if self.language != "en":
            raise ValueError("language must be 'en'.")
        if not isinstance(self.date, date):
            raise TypeError("date must be a datetime.date.")
        if not isinstance(self.favorite, str):
            raise TypeError("favorite must be a string.")
        if not isinstance(self.improvement, str):
            raise TypeError("improvement must be a string.")
        if not self.favorite.strip():
            raise ValueError("favorite must not be empty.")
        if not self.improvement.strip():
            raise ValueError("improvement must not be empty.")


@dataclass(frozen=True)
class TranslatedReview:
    """A review with its free-text fields translated to Kiswahili."""

    rating: float
    language: str
    date: date
    favorite: str
    improvement: str

    def __post_init__(self) -> None:
        if self.language != "sw":
            raise ValueError("language must be 'sw'.")
