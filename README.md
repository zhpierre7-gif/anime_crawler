# AnimeCrawler AI

**Mini advanced Python crawler for MyAnimeList data**  
Powered by the free & open [Jikan API](https://jikan.moe) (unofficial MyAnimeList API).

A clean, well-documented, production-style mini project that demonstrates modern Python practices:

- Fully asynchronous (`aiohttp` + `asyncio`)
- Strict rate limiting (respects Jikan’s 3 req/s limit)
- Pydantic models for type safety & validation
- Content-based recommendation engine (lightweight “AI”)
- Beautiful CLI powered by Typer + Rich
- Concurrent multi-page fetching
- Easy JSON export

---

## Features

| Feature | Description |
|---------|-------------|
| **Search** | Search anime by title/keywords with filters (score, type, status) |
| **Top lists** | Fetch top ranked anime (overall, airing, upcoming, by popularity...) |
| **Seasonal** | Get current season or any historical season |
| **Details** | Full anime info by MAL ID |
| **Random** | Surprise me with a random anime |
| **Recommend** | Simple content-based recommendations (genre Jaccard + score proximity) |
| **Enrich** | Batch-fetch full details for a list of anime |
| **Export** | Save results as clean JSON |

---

## Requirements

- Python 3.10+
- Internet connection (calls `https://api.jikan.moe/v4`)

---

## Installation

```bash
# Clone or extract the project
cd anime_crawler

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Quick Start

```bash
# Search
python main.py search "fullmetal alchemist" --limit 10

# Top anime
python main.py top --limit 15

# Current season
python main.py seasonal --limit 20

# Specific season
python main.py seasonal --year 2023 --season spring

# Detailed info
python main.py info 5114

# Random anime
python main.py random

# Recommendations (seed = Fullmetal Alchemist Brotherhood)
python main.py recommend 5114 --from-search "action fantasy" --limit 8

# Save results to JSON
python main.py search "steins gate" -o results.json
```

---

## Project Structure

```
anime_crawler/
├── anime_crawler/          # Main package
│   ├── __init__.py
│   ├── client.py           # Async Jikan API client + rate limiting
│   ├── crawler.py          # High-level intelligent crawler + recommendations
│   └── models.py           # Pydantic data models
├── main.py                 # CLI entry point (Typer)
├── requirements.txt
├── README.md               # This file (English)
├── README.pt.md            # Portuguese version
└── .gitignore
```

---

## Architecture Highlights

### Rate Limiting
The client uses `asyncio-throttle` and stays under Jikan’s official limits (3 requests/second, 60/minute). On HTTP 429 it automatically backs off using the `Retry-After` header.

### Recommendation Engine
A simple but effective content-based filter:

1. **Genre overlap** (Jaccard similarity) – 65% weight  
2. **Score proximity** – 20% weight  
3. **Same type bonus** (TV/Movie/OVA) – 15% weight  

No external ML libraries required – pure Python, fast and transparent.

### Concurrency Model
- Search can fetch multiple pages concurrently
- Enrichment uses a semaphore (max 2 concurrent full fetches)
- All requests go through the shared throttler

---

## Using as a Library

```python
import asyncio
from anime_crawler import AnimeCrawler

async def main():
    async with AnimeCrawler() as crawler:
        # Search
        result = await crawler.search("one punch man", limit=10)
        crawler.print_table(result.anime_list)

        # Recommend
        seed = result.anime_list[0]
        recs = crawler.recommend(seed, result.anime_list, top_k=5)
        for anime, score in recs:
            print(f"{anime.title} → {score:.3f}")

asyncio.run(main())
```

---

## API Source

This project uses **[Jikan API v4](https://docs.api.jikan.moe/)**:

- Free, no API key required
- Unofficial MyAnimeList API
- Base URL: `https://api.jikan.moe/v4`
- Please respect the rate limits and terms of service

---

## License

MIT – feel free to use, modify and learn from this code.

---

## Author Notes

Created as a clean educational example of:

- Modern async Python
- API client design
- Rate limiting patterns
- Lightweight recommendation systems
- Beautiful CLIs with Typer + Rich
- Proper project documentation (EN + PT)

Enjoy exploring anime data! 🎌
