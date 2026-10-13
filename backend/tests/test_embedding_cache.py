from types import SimpleNamespace

import app.retrieval.embeddings as embeddings


def test_repeated_query_embedding_is_cached(monkeypatch):
    calls = []

    class FakeModels:
        def embed_content(self, *, model, contents):
            calls.append((model, contents))
            return SimpleNamespace(
                embeddings=[SimpleNamespace(values=[0.125, 0.25, 0.5])]
            )

    class FakeClient:
        models = FakeModels()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(embeddings, "_get_client", lambda _api_key: FakeClient())
    embeddings._embed_single_query.cache_clear()

    try:
        first = embeddings.embed_texts(["same query"])
        second = embeddings.embed_texts(["same query"])

        assert first == second == [[0.125, 0.25, 0.5]]
        assert calls == [(embeddings.EMBEDDING_MODEL, ["same query"])]
    finally:
        embeddings._embed_single_query.cache_clear()
