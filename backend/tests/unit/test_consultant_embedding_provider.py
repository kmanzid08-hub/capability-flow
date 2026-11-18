from types import SimpleNamespace

import pytest

from app.services.consultant_retrieval import ConsultantEvidenceRetriever


@pytest.mark.asyncio
async def test_gemini_document_embeddings_use_fixed_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[tuple[object, object]] = []

    class FakeModels:
        async def embed_content(self, *, model: str, contents: list[str], config: object):
            observed.append((model, config))
            return SimpleNamespace(
                embeddings=[SimpleNamespace(values=[1.0] + [0.0] * 1535) for _ in contents]
            )

    class FakeClient:
        def __init__(self, *, api_key: str) -> None:
            assert api_key == "test-key"
            self.aio = self
            self.models = FakeModels()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_: object):
            return False

    monkeypatch.setattr("app.services.consultant_retrieval.genai.Client", FakeClient)
    vectors = await ConsultantEvidenceRetriever._embeddings(
        ["Soil testing", "Agricultural Economics"],
        api_key="test-key",
        provider="gemini",
        model="gemini-embedding-001",
        task="RETRIEVAL_DOCUMENT",
    )
    assert len(vectors) == 2
    assert all(len(vector) == 1536 for vector in vectors)
    assert observed[0][0] == "gemini-embedding-001"
    assert getattr(observed[0][1], "output_dimensionality") == 1536
    assert getattr(observed[0][1], "task_type") == "RETRIEVAL_DOCUMENT"


@pytest.mark.asyncio
async def test_bad_embedding_size_fails_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeModels:
        async def embed_content(self, *, model: str, contents: list[str], config: object):
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0, 2.0])])

    class FakeClient:
        def __init__(self, *, api_key: str) -> None:
            self.aio = self
            self.models = FakeModels()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_: object):
            return False

    monkeypatch.setattr("app.services.consultant_retrieval.genai.Client", FakeClient)
    with pytest.raises(ValueError, match="dimension"):
        await ConsultantEvidenceRetriever._embeddings(
            ["invalid"], api_key="test", provider="gemini",
            model="gemini-embedding-001", task="RETRIEVAL_QUERY",
        )
