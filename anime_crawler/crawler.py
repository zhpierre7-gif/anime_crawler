"""
High-level intelligent crawler built on top of JikanClient.

This module adds "smart" capabilities on top of the raw API client:
- Concurrent multi-page fetching with controlled concurrency
- Genre / score based filtering and ranking
- Simple recommendation engine (content-based using genres + score)
- Batch enrichment (fetch full details for a list of IDs)
- Clean export helpers
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .client import JikanClient
from .models import Anime, CrawlResult

logger = logging.getLogger(__name__)
console = Console()


class AnimeCrawler:
    """
    Intelligent Anime Crawler powered by Jikan API.

    Philosophy:
    - Respect the API (rate limits are enforced at client level)
    - Be concurrent but not aggressive
    - Provide useful high-level operations with a bit of "AI" flavor
      (filtering, ranking, simple recommendations)
    """

    def __init__(self, client: Optional[JikanClient] = None) -> None:
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "AnimeCrawler":
        if self._client is None:
            self._client = JikanClient()
            await self._client.__aenter__()
        return self

    async def __aexit__(self, *args) -> None:
        if self._owns_client and self._client:
            await self._client.__aexit__(*args)

    @property
    def client(self) -> JikanClient:
        if self._client is None:
            raise RuntimeError("Crawler must be used as async context manager")
        return self._client

    # ------------------------------------------------------------------
    # Core crawl operations
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        limit: int = 20,
        pages: int = 1,
        min_score: Optional[float] = None,
        type_: Optional[str] = None,
    ) -> CrawlResult:
        """
        Search for anime and optionally fetch multiple pages concurrently.
        """
        console.print(f"[bold cyan]Searching[/] for [yellow]{query}[/]...")

        tasks = [
            self.client.search_anime(
                query=query,
                limit=25,
                page=page,
                min_score=min_score,
                type_=type_,
            )
            for page in range(1, pages + 1)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        anime_list: list[Anime] = []
        for res in results:
            if isinstance(res, Exception):
                logger.error("Page failed: %s", res)
                continue
            anime_list.extend(res.data)

        # Deduplicate by mal_id (keep first occurrence)
        seen = set()
        unique: list[Anime] = []
        for a in anime_list:
            if a.mal_id not in seen:
                seen.add(a.mal_id)
                unique.append(a)

        # Sort by score descending (smart ranking)
        unique.sort(key=lambda x: x.score or 0.0, reverse=True)
        unique = unique[:limit]

        return CrawlResult(
            query=query,
            total_fetched=len(unique),
            anime_list=unique,
        )

    async def top(
        self,
        limit: int = 25,
        type_: Optional[str] = None,
        filter_: Optional[str] = None,
    ) -> CrawlResult:
        """Fetch top ranked anime."""
        console.print("[bold cyan]Fetching top anime...[/]")
        result = await self.client.get_top_anime(
            type_=type_, filter_=filter_, limit=limit
        )
        return CrawlResult(
            query=f"top:{filter_ or 'all'}",
            total_fetched=len(result.data),
            anime_list=result.data,
        )

    async def seasonal(
        self,
        year: Optional[int] = None,
        season: Optional[str] = None,
        limit: int = 25,
    ) -> CrawlResult:
        """Fetch current or specific season anime."""
        label = f"{season} {year}" if year and season else "current season"
        console.print(f"[bold cyan]Fetching[/] {label}...")
        result = await self.client.get_seasonal(year=year, season=season)
        anime = result.data[:limit]
        return CrawlResult(
            query=label,
            total_fetched=len(anime),
            anime_list=anime,
        )

    async def enrich(self, anime_list: list[Anime], full: bool = True) -> list[Anime]:
        """
        Enrich a list of basic anime entries with full details.
        Uses controlled concurrency to respect rate limits.
        """
        console.print(f"[bold cyan]Enriching[/] {len(anime_list)} entries...")

        semaphore = asyncio.Semaphore(2)  # max 2 concurrent full fetches

        async def _fetch_one(a: Anime) -> Anime:
            async with semaphore:
                try:
                    return await self.client.get_anime(a.mal_id, full=full)
                except Exception as exc:
                    logger.warning("Failed to enrich %s: %s", a.mal_id, exc)
                    return a

        tasks = [_fetch_one(a) for a in anime_list]
        enriched = await asyncio.gather(*tasks)
        return list(enriched)

    # ------------------------------------------------------------------
    # "AI" / Smart features
    # ------------------------------------------------------------------

    def recommend(
        self,
        seed: Anime,
        candidates: list[Anime],
        top_k: int = 5,
    ) -> list[tuple[Anime, float]]:
        """
        Simple content-based recommendation.

        Score is based on:
        - Genre overlap (Jaccard similarity)
        - Score proximity
        - Same type bonus

        Returns list of (anime, similarity_score) sorted descending.
        """
        seed_genres = set(seed.genre_names)
        if not seed_genres:
            # Fallback: just return highest scored
            ranked = sorted(
                [c for c in candidates if c.mal_id != seed.mal_id],
                key=lambda x: x.score or 0,
                reverse=True,
            )
            return [(a, 0.0) for a in ranked[:top_k]]

        scored: list[tuple[Anime, float]] = []
        for cand in candidates:
            if cand.mal_id == seed.mal_id:
                continue

            cand_genres = set(cand.genre_names)
            if not cand_genres:
                continue

            # Jaccard similarity
            intersection = len(seed_genres & cand_genres)
            union = len(seed_genres | cand_genres)
            jaccard = intersection / union if union else 0.0

            # Score proximity (normalized)
            score_sim = 0.0
            if seed.score and cand.score:
                score_sim = 1.0 - abs(seed.score - cand.score) / 10.0

            # Type bonus
            type_bonus = 0.15 if seed.type and seed.type == cand.type else 0.0

            final = (jaccard * 0.65) + (score_sim * 0.20) + type_bonus
            scored.append((cand, round(final, 4)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def analyze_genres(self, anime_list: list[Anime]) -> dict[str, int]:
        """Return frequency of genres in a collection (useful for insights)."""
        counter: Counter[str] = Counter()
        for a in anime_list:
            counter.update(a.genre_names)
        return dict(counter.most_common())

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def export_json(self, result: CrawlResult, path: str | Path) -> Path:
        """Save crawl result to a pretty JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        console.print(f"[green]✓[/] Exported {result.total_fetched} entries → [cyan]{path}[/]")
        return path

    def print_table(self, anime_list: list[Anime], title: str = "Results") -> None:
        """Pretty print results using rich."""
        from rich.table import Table

        table = Table(title=title, show_lines=False)
        table.add_column("ID", style="dim", width=7)
        table.add_column("Title", style="bold")
        table.add_column("Type", width=8)
        table.add_column("Eps", justify="right", width=5)
        table.add_column("Score", justify="right", width=6)
        table.add_column("Genres", style="italic")

        for a in anime_list:
            genres = ", ".join(a.genre_names[:3])
            if len(a.genre_names) > 3:
                genres += "..."
            table.add_row(
                str(a.mal_id),
                (a.title or "?")[:45],
                a.type or "?",
                str(a.episodes or "?"),
                f"{a.score:.2f}" if a.score else "—",
                genres,
            )

        console.print(table)
