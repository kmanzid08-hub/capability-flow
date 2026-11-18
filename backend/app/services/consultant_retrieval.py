"""Evidence-level hybrid retrieval for consultant shortlisting.

This never certifies qualification. Retrieval scores are used only to select
candidates for the existing deterministic, evidence-backed matching engine.
"""
import hashlib
import logging
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.matching import PersonProfile

logger = logging.getLogger(__name__)
_WORDS = re.compile(r"[a-z0-9]+")
_STOP = frozenset({
    "and", "the", "for", "with", "from", "this", "that", "must", "have",
    "years", "year", "experience", "required", "consultant", "expert",
    "qualification", "qualifications", "minimum", "role", "of", "in", "to",
    "a", "an", "on", "or", "at", "as", "by", "is",
})


@dataclass(frozen=True)
class EvidenceRecord:
    person_id: uuid.UUID
    evidence_type: str
    evidence_id: uuid.UUID
    content: str

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RetrievalHit:
    person_id: uuid.UUID
    score: float
    evidence_type: str
    evidence_id: uuid.UUID
    excerpt: str


def evidence_records(profile: PersonProfile) -> list[EvidenceRecord]:
    """Use approved structured CV evidence; never embed personal contact data."""
    person = profile.person
    entries: list[EvidenceRecord] = []

    def add(category: str, source: Any, *values: object) -> None:
        content = " | ".join(str(v).strip() for v in values if v is not None and str(v).strip())
        if content:
            entries.append(EvidenceRecord(person.id, category, source.id, content[:6000]))

    for item in profile.skills:
        add("skill", item, item.name, item.notes, item.years_experience)
    for item in profile.education:
        add("education", item, item.degree_level.value, item.degree_name, item.field_of_study)
    for item in profile.certifications:
        add("certification", item, item.name, item.issuer, item.notes)
    for item in profile.employment:
        add(
            "employment", item, item.job_title, item.industry, item.description,
            item.responsibilities, item.achievements, item.country,
        )
    for item in profile.projects:
        add(
            "project", item, item.project_name, item.role, item.sector,
            item.description, item.responsibilities, item.outcomes,
            item.skills_summary, item.country,
        )
    # Do not store raw CV text, phone numbers or emails in the vector index.
    return entries


def query_terms(query: str) -> set[str]:
    return {word for word in _WORDS.findall(query.lower()) if len(word) > 2 and word not in _STOP}


class ConsultantEvidenceRetriever:
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        self.session = session
        self.organization_id = organization_id

    async def refresh(self, profiles: list[PersonProfile]) -> int:
        """Incremental, tenant-scoped sync. Never delete records for omitted profiles."""
        count = 0
        for profile in profiles:
            records = evidence_records(profile)
            existing_result = await self.session.execute(
                text(
                    "SELECT evidence_type, evidence_id, content_hash "
                    "FROM consultant_evidence_index "
                    "WHERE organization_id=:org AND person_id=:person"
                ),
                {"org": self.organization_id, "person": profile.person.id},
            )
            existing = {(row.evidence_type, row.evidence_id): row.content_hash
                        for row in existing_result}
            current = {(record.evidence_type, record.evidence_id) for record in records}
            for record in records:
                key = (record.evidence_type, record.evidence_id)
                if existing.get(key) == record.digest:
                    continue
                await self.session.execute(
                    text(
                        "INSERT INTO consultant_evidence_index "
                        "(organization_id, person_id, evidence_type, evidence_id, content, "
                        "content_hash, embedding_model, embedding) "
                        "VALUES (:org, :person, :kind, :evidence, :content, :digest, NULL, NULL) "
                        "ON CONFLICT (organization_id, person_id, evidence_type, evidence_id) "
                        "DO UPDATE SET content=EXCLUDED.content, "
                        "content_hash=EXCLUDED.content_hash, embedding=NULL, "
                        "embedding_model=NULL, updated_at=now()"
                    ),
                    {
                        "org": self.organization_id, "person": record.person_id,
                        "kind": record.evidence_type, "evidence": record.evidence_id,
                        "content": record.content, "digest": record.digest,
                    },
                )
                count += 1
            for kind, evidence_id in existing.keys() - current:
                await self.session.execute(
                    text(
                        "DELETE FROM consultant_evidence_index "
                        "WHERE organization_id=:org AND person_id=:person "
                        "AND evidence_type=:kind AND evidence_id=:evidence"
                    ),
                    {"org": self.organization_id, "person": profile.person.id,
                     "kind": kind, "evidence": evidence_id},
                )
        return count

    async def embed_missing(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        batch_size: int = 32,
    ) -> int:
        """Index only missing vectors. Explicit opt-in key prevents surprise billing."""
        client = AsyncOpenAI(api_key=api_key, timeout=90.0, max_retries=1)
        result = await self.session.execute(
            text(
                "SELECT person_id, evidence_type, evidence_id, content "
                "FROM consultant_evidence_index "
                "WHERE organization_id=:org "
                "AND (embedding IS NULL OR embedding_model != :model) "
                "ORDER BY person_id, evidence_type, evidence_id"
            ),
            {"org": self.organization_id, "model": model},
        )
        rows = list(result)
        await self.session.commit()
        completed = 0
        for offset in range(0, len(rows), batch_size):
            batch = rows[offset : offset + batch_size]
            response = await client.embeddings.create(
                model=model, input=[item.content for item in batch],
                dimensions=1536,
            )
            vectors = sorted(response.data, key=lambda item: item.index)
            if len(vectors) != len(batch):
                raise ValueError("Embedding provider returned the wrong number of vectors")
            for item, vector in zip(batch, vectors, strict=True):
                if len(vector.embedding) != 1536:
                    raise ValueError("Embedding dimension mismatch")
                literal = "[" + ",".join(str(v) for v in vector.embedding) + "]"
                await self.session.execute(
                    text(
                        "UPDATE consultant_evidence_index "
                        "SET embedding=CAST(:embedding AS vector), "
                        "embedding_model=:model, updated_at=now() "
                        "WHERE organization_id=:org AND person_id=:person "
                        "AND evidence_type=:kind AND evidence_id=:evidence "
                        "AND embedding IS NULL"
                    ),
                    {
                        "org": self.organization_id, "person": item.person_id,
                        "kind": item.evidence_type, "evidence": item.evidence_id,
                        "model": model, "embedding": literal,
                    },
                )
                completed += 1
            await self.session.commit()
        return completed

    @staticmethod
    async def embed_query(
        query: str, *, api_key: str, model: str = "text-embedding-3-small"
    ) -> list[float]:
        client = AsyncOpenAI(api_key=api_key, timeout=90.0, max_retries=1)
        response = await client.embeddings.create(
            model=model, input=query[:8000], dimensions=1536
        )
        vector = response.data[0].embedding
        if len(vector) != 1536:
            raise ValueError("Embedding dimension mismatch")
        return vector

    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 100,
        query_embedding: list[float] | None = None,
    ) -> list[RetrievalHit]:
        """Lexical + optional pgvector exact cosine distance, deduplicated by person.

        The SQL scope is always organization_id and returned IDs still require
        final deterministic evaluation. No score here proves eligibility.
        """
        limit = max(1, min(limit, 500))
        if query_embedding is not None and len(query_embedding) != 1536:
            raise ValueError("Expected 1536-dimensional query embedding")
        terms = query_terms(query)
        lexical_query = " ".join(sorted(terms))
        if not lexical_query and query_embedding is None:
            return []
        parameters: dict[str, Any] = {
            "org": self.organization_id, "query": lexical_query, "limit": limit * 8,
        }
        vector_expression = "0.0"
        if query_embedding is not None:
            parameters["embedding"] = "[" + ",".join(f"{float(v):.8f}" for v in query_embedding) + "]"
            vector_expression = (
                "CASE WHEN embedding IS NULL THEN 0.0 ELSE "
                "GREATEST(0.0, 1.0 - (embedding <=> CAST(:embedding AS vector))) END"
            )
        statement = text(
            "SELECT person_id, evidence_type, evidence_id, content, "
            "ts_rank_cd(to_tsvector('simple', content), "
            "plainto_tsquery('simple', :query)) AS lexical, "
            + vector_expression + " AS semantic "
            "FROM consultant_evidence_index "
            "WHERE organization_id=:org "
            "ORDER BY (ts_rank_cd(to_tsvector('simple', content), "
            "plainto_tsquery('simple', :query)) + "
            + vector_expression + ") DESC LIMIT :limit"
        )
        results = await self.session.execute(statement, parameters)
        best: dict[uuid.UUID, RetrievalHit] = {}
        for row in results:
            score = float(row.lexical or 0) + float(row.semantic or 0)
            if score <= 0:
                continue
            hit = RetrievalHit(row.person_id, score, row.evidence_type, row.evidence_id,
                               row.content[:450])
            if row.person_id not in best or best[row.person_id].score < hit.score:
                best[row.person_id] = hit
        return sorted(best.values(), key=lambda hit: (-hit.score, str(hit.person_id)))[:limit]


def summarize_shadow_recall(
    baseline: list[uuid.UUID], retrieved: set[uuid.UUID]
) -> tuple[int, int]:
    """Count baseline top candidates retained by retrieval without altering rankings."""
    return sum(person_id in retrieved for person_id in baseline), len(baseline)
