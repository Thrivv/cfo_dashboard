"""Reranking using Hugging Face CrossEncoder (direct)."""
from sentence_transformers import CrossEncoder

# Download directly from Hugging Face
ranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank(query: str, docs: list[str], top_n: int = 3) -> list[str]:
    if not docs:
        return []
    pairs = [(query, doc) for doc in docs]
    scores = ranker.predict(pairs)
    sorted_docs = [doc for _, doc in sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)]
    return sorted_docs[:top_n]

# ---------------------------------------------------------------------------
# Example usage (for quick local test)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_query = "What is the capital of France?"
    test_docs = [
        "The Eiffel Tower is located in Paris.",
        "France is a country in Europe.",
        "The capital of France is Paris.",
        "Paris is a city known for its art museums."
    ]

    reranked_docs = rerank(test_query, test_docs, top_n=2)
    print(f"Query: {test_query}")
    print("Reranked Documents:")
    for doc in reranked_docs:
        print(f"- {doc}")
