#!/usr/bin/env python3
"""
AnimeCrawler AI - CLI entry point.

Examples:
    python main.py search "fullmetal alchemist" --limit 10
    python main.py top --limit 15
    python main.py seasonal --limit 20
    python main.py recommend 5114 --from-search "action" --limit 8
    python main.py random
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from anime_crawler import AnimeCrawler
from anime_crawler.models import Anime

app = typer.Typer(
    name="anime-crawler",
    help="Mini advanced AI-powered crawler for MyAnimeList data (via Jikan API)",
    add_completion=False,
)
console = Console()


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)],
    )


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (anime title or keywords)"),
    limit: int = typer.Option(15, "--limit", "-l", help="Max results to return"),
    pages: int = typer.Option(1, "--pages", "-p", help="Number of pages to fetch"),
    min_score: Optional[float] = typer.Option(None, "--min-score", help="Minimum score filter"),
    type_: Optional[str] = typer.Option(None, "--type", help="Filter: tv, movie, ova..."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save JSON to file"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Search for anime by title / keywords."""
    setup_logging(verbose)

    async def _run() -> None:
        async with AnimeCrawler() as crawler:
            result = await crawler.search(
                query=query,
                limit=limit,
                pages=pages,
                min_score=min_score,
                type_=type_,
            )
            crawler.print_table(result.anime_list, title=f"Search: {query}")
            if output:
                crawler.export_json(result, output)

    asyncio.run(_run())


@app.command()
def top(
    limit: int = typer.Option(25, "--limit", "-l"),
    type_: Optional[str] = typer.Option(None, "--type", help="tv, movie, ova..."),
    filter_: Optional[str] = typer.Option(
        None, "--filter", help="airing, upcoming, bypopularity, favorite"
    ),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Fetch top ranked anime from MyAnimeList."""
    setup_logging(verbose)

    async def _run() -> None:
        async with AnimeCrawler() as crawler:
            result = await crawler.top(limit=limit, type_=type_, filter_=filter_)
            crawler.print_table(result.anime_list, title="Top Anime")
            if output:
                crawler.export_json(result, output)

    asyncio.run(_run())


@app.command()
def seasonal(
    year: Optional[int] = typer.Option(None, "--year", "-y"),
    season: Optional[str] = typer.Option(
        None, "--season", "-s", help="winter, spring, summer, fall"
    ),
    limit: int = typer.Option(20, "--limit", "-l"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Fetch anime from the current (or specified) season."""
    setup_logging(verbose)

    async def _run() -> None:
        async with AnimeCrawler() as crawler:
            result = await crawler.seasonal(year=year, season=season, limit=limit)
            title = f"Seasonal: {season} {year}" if year and season else "Current Season"
            crawler.print_table(result.anime_list, title=title)
            if output:
                crawler.export_json(result, output)

    asyncio.run(_run())


@app.command()
def recommend(
    mal_id: int = typer.Argument(..., help="MAL ID of the seed anime"),
    from_search: Optional[str] = typer.Option(
        None, "--from-search", help="Search query used as candidate pool"
    ),
    limit: int = typer.Option(8, "--limit", "-l", help="How many recommendations"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """
    Get simple content-based recommendations for a given anime.

    Uses genre overlap + score proximity (lightweight "AI").
    """
    setup_logging(verbose)

    async def _run() -> None:
        async with AnimeCrawler() as crawler:
            # 1. Get the seed anime
            seed = await crawler.client.get_anime(mal_id, full=True)
            console.print(f"\n[bold]Seed:[/] {seed.summary()}")
            console.print(f"Genres: {', '.join(seed.genre_names)}\n")

            # 2. Build candidate pool
            if from_search:
                pool_result = await crawler.search(from_search, limit=50, pages=2)
                candidates = pool_result.anime_list
            else:
                # Default: use top anime + same genres roughly
                top_result = await crawler.top(limit=50)
                candidates = top_result.anime_list

            # 3. Recommend
            recs = crawler.recommend(seed, candidates, top_k=limit)

            console.print("[bold green]Recommendations:[/]\n")
            for i, (anime, score) in enumerate(recs, 1):
                console.print(
                    f"  {i}. [cyan]{anime.title}[/] "
                    f"(score {anime.score or 'N/A'}) "
                    f"— similarity [yellow]{score:.3f}[/]"
                )
                console.print(f"     Genres: {', '.join(anime.genre_names[:5])}")

    asyncio.run(_run())


@app.command()
def random(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Fetch a completely random anime (surprise me!)."""
    setup_logging(verbose)

    async def _run() -> None:
        async with AnimeCrawler() as crawler:
            anime = await crawler.client.get_random_anime()
            console.print("\n[bold magenta]🎲 Random Anime[/]\n")
            console.print(f"[bold]{anime.title}[/] ({anime.title_japanese or ''})")
            console.print(f"Type: {anime.type} | Episodes: {anime.episodes or '?'}")
            console.print(f"Score: {anime.score or 'N/A'} | Rank: {anime.rank or 'N/A'}")
            console.print(f"Genres: {', '.join(anime.genre_names)}")
            if anime.synopsis:
                console.print(f"\n{anime.synopsis[:400]}...")

    asyncio.run(_run())


@app.command()
def info(
    mal_id: int = typer.Argument(..., help="MyAnimeList ID"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Show detailed information about a specific anime."""
    setup_logging(verbose)

    async def _run() -> None:
        async with AnimeCrawler() as crawler:
            anime = await crawler.client.get_anime(mal_id, full=True)
            console.print(f"\n[bold cyan]{anime.title}[/]")
            if anime.title_english:
                console.print(f"English: {anime.title_english}")
            if anime.title_japanese:
                console.print(f"Japanese: {anime.title_japanese}")
            console.print(f"\nMAL ID: {anime.mal_id}")
            console.print(f"Type: {anime.type} | Status: {anime.status}")
            console.print(f"Episodes: {anime.episodes or '?'} | Duration: {anime.duration}")
            console.print(f"Score: {anime.score or 'N/A'} ({anime.scored_by or 0} users)")
            console.print(f"Rank: #{anime.rank or '?'} | Popularity: #{anime.popularity or '?'}")
            console.print(f"Genres: {', '.join(anime.genre_names)}")
            if anime.studios:
                console.print(f"Studios: {', '.join(s.name for s in anime.studios)}")
            if anime.synopsis:
                console.print(f"\n[bold]Synopsis[/]\n{anime.synopsis}")

    asyncio.run(_run())


if __name__ == "__main__":
    app()
