"""
Pydantic models for Jikan API responses.
These models provide type safety, validation and clean serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ImageSet(BaseModel):
    """Image URLs in different sizes."""

    image_url: Optional[str] = None
    small_image_url: Optional[str] = None
    large_image_url: Optional[str] = None


class Images(BaseModel):
    """Container for jpg/webp image sets."""

    jpg: Optional[ImageSet] = None
    webp: Optional[ImageSet] = None


class Genre(BaseModel):
    """Anime genre."""

    mal_id: int
    type: Optional[str] = None
    name: str
    url: Optional[str] = None


class Studio(BaseModel):
    """Animation studio."""

    mal_id: int
    type: Optional[str] = None
    name: str
    url: Optional[str] = None


class Aired(BaseModel):
    """Air dates information."""

    from_: Optional[str] = Field(None, alias="from")
    to: Optional[str] = None
    string: Optional[str] = None

    model_config = {"populate_by_name": True}


class Anime(BaseModel):
    """
    Core Anime model representing a single anime entry from Jikan/MAL.

    This is the main data structure used throughout the crawler.
    """

    mal_id: int
    url: Optional[str] = None
    images: Optional[Images] = None
    trailer: Optional[dict[str, Any]] = None
    approved: Optional[bool] = None
    titles: Optional[list[dict[str, str]]] = None
    title: Optional[str] = None
    title_english: Optional[str] = None
    title_japanese: Optional[str] = None
    title_synonyms: Optional[list[str]] = None
    type: Optional[str] = None  # TV, Movie, OVA, etc.
    source: Optional[str] = None
    episodes: Optional[int] = None
    status: Optional[str] = None  # Finished Airing, Currently Airing, etc.
    airing: Optional[bool] = None
    aired: Optional[Aired] = None
    duration: Optional[str] = None
    rating: Optional[str] = None  # G, PG-13, R, etc.
    score: Optional[float] = None
    scored_by: Optional[int] = None
    rank: Optional[int] = None
    popularity: Optional[int] = None
    members: Optional[int] = None
    favorites: Optional[int] = None
    synopsis: Optional[str] = None
    background: Optional[str] = None
    season: Optional[str] = None
    year: Optional[int] = None
    broadcast: Optional[dict[str, Any]] = None
    producers: Optional[list[Studio]] = None
    licensors: Optional[list[Studio]] = None
    studios: Optional[list[Studio]] = None
    genres: Optional[list[Genre]] = None
    explicit_genres: Optional[list[Genre]] = None
    themes: Optional[list[Genre]] = None
    demographics: Optional[list[Genre]] = None

    @property
    def main_image(self) -> Optional[str]:
        """Return the best available image URL."""
        if self.images and self.images.jpg:
            return (
                self.images.jpg.large_image_url
                or self.images.jpg.image_url
                or self.images.jpg.small_image_url
            )
        return None

    @property
    def genre_names(self) -> list[str]:
        """List of genre names for easy access."""
        return [g.name for g in (self.genres or [])]

    def summary(self) -> str:
        """Short human-readable summary."""
        score = f"{self.score:.2f}" if self.score else "N/A"
        eps = self.episodes or "?"
        return (
            f"[{self.mal_id}] {self.title} "
            f"({self.type or '?'} • {eps} eps • Score: {score})"
        )


class Pagination(BaseModel):
    """Pagination metadata from Jikan list endpoints."""

    last_visible_page: int = 1
    has_next_page: bool = False
    current_page: int = 1
    items: Optional[dict[str, Any]] = None


class AnimeSearchResult(BaseModel):
    """Response wrapper for search / list endpoints."""

    data: list[Anime] = Field(default_factory=list)
    pagination: Optional[Pagination] = None


class CrawlResult(BaseModel):
    """
    Result object returned by the high-level crawler methods.
    Contains the fetched data + metadata about the crawl.
    """

    query: Optional[str] = None
    total_fetched: int = 0
    anime_list: list[Anime] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = "jikan-v4"

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON export."""
        return {
            "query": self.query,
            "total_fetched": self.total_fetched,
            "fetched_at": self.fetched_at.isoformat(),
            "source": self.source,
            "anime": [a.model_dump(mode="json") for a in self.anime_list],
        }
