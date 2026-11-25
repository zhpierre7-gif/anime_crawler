# AnimeCrawler AI

**Mini crawler avançado em Python para dados do MyAnimeList**  
Powered by a API gratuita e aberta [Jikan](https://jikan.moe) (API não-oficial do MyAnimeList).

Um projeto mini, limpo, bem documentado e com cara de produção que demonstra boas práticas modernas de Python:

- Totalmente assíncrono (`aiohttp` + `asyncio`)
- Rate limiting rigoroso (respeita o limite de 3 req/s da Jikan)
- Modelos Pydantic para type safety e validação
- Motor de recomendação baseado em conteúdo (leve “IA”)
- CLI bonita com Typer + Rich
- Busca multi-página concorrente
- Exportação fácil para JSON

---

## Funcionalidades

| Funcionalidade | Descrição |
|----------------|-----------|
| **Search** | Busca anime por título/palavras-chave com filtros (score, tipo, status) |
| **Top lists** | Top animes ranqueados (geral, airing, upcoming, por popularidade...) |
| **Seasonal** | Temporada atual ou qualquer temporada histórica |
| **Details** | Informações completas de um anime pelo ID do MAL |
| **Random** | Anime aleatório (me surpreenda!) |
| **Recommend** | Recomendações baseadas em conteúdo (Jaccard de gêneros + proximidade de score) |
| **Enrich** | Busca em lote dos detalhes completos de uma lista de animes |
| **Export** | Salva resultados em JSON limpo |

---

## Requisitos

- Python 3.10+
- Conexão com a internet (chama `https://api.jikan.moe/v4`)

---

## Instalação

```bash
# Entre na pasta do projeto
cd anime_crawler

# Crie um ambiente virtual (recomendado)
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# Instale as dependências
pip install -r requirements.txt
```

---

## Uso Rápido

```bash
# Busca
python main.py search "fullmetal alchemist" --limit 10

# Top animes
python main.py top --limit 15

# Temporada atual
python main.py seasonal --limit 20

# Temporada específica
python main.py seasonal --year 2023 --season spring

# Informações detalhadas
python main.py info 5114

# Anime aleatório
python main.py random

# Recomendações (semente = Fullmetal Alchemist Brotherhood)
python main.py recommend 5114 --from-search "action fantasy" --limit 8

# Salvar resultados em JSON
python main.py search "steins gate" -o results.json
```

---

## Estrutura do Projeto

```
anime_crawler/
├── anime_crawler/          # Pacote principal
│   ├── __init__.py
│   ├── client.py           # Cliente assíncrono da API Jikan + rate limiting
│   ├── crawler.py          # Crawler inteligente de alto nível + recomendações
│   └── models.py           # Modelos de dados Pydantic
├── main.py                 # Entrada da CLI (Typer)
├── requirements.txt
├── README.md               # Versão em inglês
├── README.pt.md            # Esta versão em português
└── .gitignore
```

---

## Destaques de Arquitetura

### Rate Limiting
O cliente usa `asyncio-throttle` e fica abaixo dos limites oficiais da Jikan (3 requisições/segundo, 60/minuto). Em caso de HTTP 429 faz backoff automático usando o header `Retry-After`.

### Motor de Recomendação
Um filtro baseado em conteúdo simples porém eficaz:

1. **Sobreposição de gêneros** (similaridade de Jaccard) – peso 65%  
2. **Proximidade de score** – peso 20%  
3. **Bônus de mesmo tipo** (TV/Movie/OVA) – peso 15%  

Sem bibliotecas de Machine Learning externas – Python puro, rápido e transparente.

### Modelo de Concorrência
- A busca pode buscar várias páginas de forma concorrente
- O enrich usa um semáforo (máximo 2 fetches completos concorrentes)
- Todas as requisições passam pelo throttler compartilhado

---

## Usando como Biblioteca

```python
import asyncio
from anime_crawler import AnimeCrawler

async def main():
    async with AnimeCrawler() as crawler:
        # Busca
        result = await crawler.search("one punch man", limit=10)
        crawler.print_table(result.anime_list)

        # Recomendações
        seed = result.anime_list[0]
        recs = crawler.recommend(seed, result.anime_list, top_k=5)
        for anime, score in recs:
            print(f"{anime.title} → {score:.3f}")

asyncio.run(main())
```

---

## Fonte da API

Este projeto utiliza a **[Jikan API v4](https://docs.api.jikan.moe/)**:

- Gratuita, sem necessidade de API key
- API não-oficial do MyAnimeList
- Base URL: `https://api.jikan.moe/v4`
- Por favor respeite os rate limits e os termos de serviço

---

## Licença

MIT – sinta-se livre para usar, modificar e aprender com este código.

---

## Notas do Autor

Criado como um exemplo educacional limpo de:

- Python assíncrono moderno
- Design de clientes de API
- Padrões de rate limiting
- Sistemas de recomendação leves
- CLIs bonitas com Typer + Rich
- Documentação adequada de projeto (EN + PT)

Aproveite explorando dados de anime! 🎌
