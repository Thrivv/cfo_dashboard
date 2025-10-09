import cohere

try:
    from .config import COHERE_API_KEY
except ImportError:
    from config import COHERE_API_KEY

co = cohere.Client(COHERE_API_KEY)


def rerank(query: str, docs: list[str], top_n: int = 3) -> list[str]:
    """Rerank documents using Cohere API."""
    if not docs:
        return []
    results = co.rerank(
        model="rerank-english-v3.0", query=query, documents=docs, top_n=top_n
    )
    return [docs[r_item.index] for r_item in results.results]
