"""Reranking utilities for document retrieval."""

from flashrank.Ranker import Ranker, RerankRequest

# Initialize the FlashRank reranker.
# The default model is 'ms-marco-MiniLM-L-12-v2', a fast and efficient option.
# You can choose a different model if needed, such as 'rank-T5-flan' for higher accuracy.
ranker = Ranker()


def rerank(query: str, docs: list[str], top_n: int = 3) -> list[str]:
    """
    Rerank documents using a local FlashRank model.

    Args:
        query (str): The search query.
        docs (list[str]): A list of documents to be reranked.
        top_n (int): The number of top documents to return.

    Returns:
        list[str]: The reranked list of documents.
    """
    if not docs:
        return []

    # Prepare the documents for the reranker.
    # FlashRank expects a list of dictionaries with 'text' and an optional 'meta' key.
    passages = [{'text': doc} for doc in docs]

    # Create the rerank request.
    rerank_request = RerankRequest(
        query=query,
        passages=passages
    )

    # Perform the reranking.
    # The `rerank()` method returns a list of dictionaries, sorted by relevance score.
    results = ranker.rerank(rerank_request)

    # Return the content of the top_n documents.
    # FlashRank automatically sorts the results for you.
    return [result['text'] for result in results[:top_n]]

