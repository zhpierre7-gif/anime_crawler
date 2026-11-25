"""
Async HTTP client for the Jikan API (unofficial MyAnimeList API).

Features:
- Built-in rate limiting (respects 3 req/s and 60 req/min)
- Automatic retries on 429 / transient errors
- Clean async context manager usage
- Typed responses via Pydantic models
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import aiohttp
from asyncio_throttle import Throttler

from .models import Anime, AnimeSearchResult

logger = logging.getLogger(__name__)

BASE_URL = "https://api.jikan.moe/v4"


class JikanClient:
    """
    Production-ready async client for Jikan API v4.

    Usage:
        async with JikanClient() as client:
            results = await client.search_anime("naruto", limit=10)
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        requests_per_second: float = 2.5,  # slightly under the 3/s limit
        max_retries: int = 3,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        # Throttler enforces the rate limit across all concurrent calls
        self._throttler = Throttler(rate_limit=requests_per_second, period=1.0)

    async def __aenter__(self) -> "JikanClient":
        self._session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers={
                "User-Agent": "AnimeCrawlerAI/1.0 (educational; +https://github.com/)",
                "Accept": "application/json",
            },
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Low-level request with rate limiting + exponential backoff on 429.
        """
        if self._session is None:
            raise RuntimeError("Client must be used as async context manager")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            async with self._throttler:
                try:
                    async with self._session.request(method, url, params=params) as resp:
                        if resp.status == 429:
                            retry_after = float(resp.headers.get("Retry-After", 2 ** attempt))
                            logger.warning(
                                "Rate limited (429). Waiting %.1fs (attempt %d/%d)",
                                retry_after,
                                attempt,
                                self.max_retries,
                            )
                            await asyncio.sleep(retry_after)
                            continue

                        resp.raise_for_status()
                        data = await resp.json()
                        return data

                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    last_exception = exc
                    wait = 2 ** attempt
                    logger.warning(
                        "Request failed (%s). Retrying in %ds... (%d/%d)",
                        type(exc).__name__,
                        wait,
                        attempt,
                        self.max_retries,
                    )
                    await asyncio.sleep(wait)

        raise RuntimeError(
            f"Failed after {self.max_retries} retries: {last_exception}"
        ) from last_exception

    # ------------------------------------------------------------------
    # Public high-level methods
    # ------------------------------------------------------------------

    async def search_anime(
        self,
        query: str,
        limit: int = 10,
        page: int = 1,
        type_: Optional[str] = None,
        status: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> AnimeSearchResult:
        """
        Search anime by title / keywords.

        Args:
            query: Search string (title, keywords...)
            limit: Max results per page (1-25 recommended)
            page: Page number (starts at 1)
            type_: Filter by type (tv, movie, ova, special, ona, music)
            status: airing, complete, upcoming
            min_score: Minimum score filter (0-10)
        """
        params: dict[str, Any] = {
            "q": query,
            "limit": min(limit, 25),
            "page": page,
        }
        if type_:
            params["type"] = type_
        if status:
            params["status"] = status
        if min_score is not None:
            params["min_score"] = min_score

        data = await self._request("GET", "/anime", params=params)
        return AnimeSearchResult.model_validate(data)

    async def get_anime(self, mal_id: int, full: bool = False) -> Anime:
        """
        Get detailed information about a single anime by MAL ID.

        Args:
            mal_id: MyAnimeList ID
            full: If True, request the /full endpoint (more fields)
        """
        endpoint = f"/anime/{mal_id}/full" if full else f"/anime/{mal_id}"
        data = await self._request("GET", endpoint)
        return Anime.model_validate(data["data"])

    async def get_top_anime(
        self,
        type_: Optional[str] = None,
        filter_: Optional[str] = None,
        page: int = 1,
        limit: int = 25,
    ) -> AnimeSearchResult:
        """
        Get top ranked anime.

        Args:
            type_: tv, movie, ova, special, ona, music
            filter_: airing, upcoming, bypopularity, favorite
            page / limit: pagination
        """
        params: dict[str, Any] = {"page": page, "limit": min(limit, 25)}
        if type_:
            params["type"] = type_
        if filter_:
            params["filter"] = filter_

        data = await self._request("GET", "/top/anime", params=params)
        return AnimeSearchResult.model_validate(data)

    async def get_seasonal(
        self,
        year: Optional[int] = None,
        season: Optional[str] = None,
        page: int = 1,
    ) -> AnimeSearchResult:
        """
        Get anime from a specific season (or current season if omitted).

        Args:
            year: e.g. 2024
            season: winter, spring, summer, fall
            page: pagination
        """
        if year and season:
            endpoint = f"/seasons/{year}/{season}"
        else:
            endpoint = "/seasons/now"

        data = await self._request("GET", endpoint, params={"page": page})
        return AnimeSearchResult.model_validate(data)

    async def get_random_anime(self) -> Anime:
        """Fetch a completely random anime (fun endpoint)."""
        data = await self._request("GET", "/random/anime")
        return Anime.model_validate(data["data"])
