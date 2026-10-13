"""Optional Gemini embeddings with client reuse and bounded query-vector caching."""
import json
import os
from functools import lru_cache

EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")


@lru_cache(maxsize=4)
def _get_client(api_key: str):
    """Reuse the SDK client across requests instead of rebuilding it for every query."""
    from google import genai
    return genai.Client(api_key=api_key)


@lru_cache(maxsize=512)
def _embed_single_query(model: str, text: str) -> tuple[float, ...]:
    """Cache repeated single-query embeddings within a process (bounded memory)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured for embeddings")
    response = _get_client(api_key).models.embed_content(model=model, contents=[text])
    items = getattr(response, "embeddings", None) or []
    if not items:
        raise RuntimeError("Embedding API returned no vectors")
    item = items[0]
    values = getattr(item, "values", None)
    if values is None and isinstance(item, dict):
        values = item.get("values")
    if not values:
        raise RuntimeError("Embedding API returned an empty vector")
    return tuple(float(value) for value in values)


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    if not texts:
        return None
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        if len(texts) == 1:
            vector = _embed_single_query(EMBEDDING_MODEL, texts[0])
            return [list(vector)] if vector else None

        # Keep ingestion efficient: embed document chunks in one batch request.
        response = _get_client(api_key).models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texts,
        )
        vectors = []
        for item in (getattr(response, "embeddings", None) or []):
            values = getattr(item, "values", None)
            if values is None and isinstance(item, dict):
                values = item.get("values")
            if not values:
                return None
            vectors.append([float(value) for value in values])
        return vectors if len(vectors) == len(texts) else None
    except Exception as exc:
        # Do not fail ingestion or investigations because embedding quota/model is unavailable.
        print(f"Relay embeddings unavailable; using keyword retrieval: {type(exc).__name__}: {exc}")
        return None


def vector_to_json(vector: list[float] | None) -> str | None:
    return json.dumps(vector, separators=(",", ":")) if vector else None


def vector_from_json(value: str | None) -> list[float] | None:
    if not value:
        return None
    try:
        result = json.loads(value)
        return [float(item) for item in result] if isinstance(result, list) else None
    except (TypeError, ValueError):
        return None
