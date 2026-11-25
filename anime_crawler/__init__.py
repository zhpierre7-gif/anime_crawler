"""
AnimeCrawler AI - Mini advanced Python crawler for MyAnimeList data
via the free Jikan API (https://jikan.moe).

Public API:
    from anime_crawler import AnimeCrawler, JikanClient
"""

from .client import JikanClient
from .crawler import AnimeCrawler
from .models import Anime, CrawlResult

__version__ = "1.0.0"
__all__ = ["AnimeCrawler", "JikanClient", "Anime", "CrawlResult"]
