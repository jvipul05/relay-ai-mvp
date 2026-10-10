"""Optional Gemini embeddings. Retrieval gracefully falls back to keyword ranking."""
import json
import os

EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    if not texts or not os.getenv("GEMINI_API_KEY"):
        return None
    try:
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.embed_content(model=EMBEDDING_MODEL, contents=texts)
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
