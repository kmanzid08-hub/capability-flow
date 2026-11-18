"""PostgreSQL + pgvector acceptance tests against a disposable migrated database."""
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.services.consultant_retrieval import ConsultantEvidenceRetriever


@pytest.mark.asyncio
async def test_tenant_isolation_person_level_retrieval_and_vector_similarity() -> None:
    database_url = os.getenv("RAG_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Requires disposable RAG_TEST_DATABASE_URL")
    engine = create_async_engine(database_url)
    org_one, org_two, user = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    first, second, different_tenant, archived = (uuid.uuid4() for _ in range(4))
    vec = "[" + ",".join(["1.0"] + ["0.0"] * 1535) + "]"
    try:
        async with AsyncSession(engine) as session:
            await session.execute(
                text(
                    "INSERT INTO organizations(id, name, slug, status) "
                    "VALUES (:a, 'First', :slug_a, 'ACTIVE'), "
                    "(:b, 'Second', :slug_b, 'ACTIVE')"
                ),
                {"a": org_one, "b": org_two,
                 "slug_a": f"rag-test-{org_one}", "slug_b": f"rag-test-{org_two}"},
            )
            await session.execute(
                text(
                    "INSERT INTO users (id,email,password_hash,full_name,is_active) "
                    "VALUES (:id, :email, 'unused', 'RAG test', true)"
                ),
                {"id": user, "email": f"rag-{user}@example.invalid"},
            )
            for person, org, status in (
                (first, org_one, "ACTIVE"),
                (second, org_one, "ACTIVE"),
                (different_tenant, org_two, "ACTIVE"),
                (archived, org_one, "ARCHIVED"),
            ):
                await session.execute(
                    text(
                        "INSERT INTO people (id, organization_id, first_name, "
                        "last_name, display_name, availability_status, "
                        "profile_status, created_by_user_id, updated_by_user_id) "
                        "VALUES (:id, :org, 'Sample', 'Consultant', 'Sample Consultant', "
                        "'UNKNOWN', :status, :user, :user)"
                    ),
                    {"id": person, "org": org, "status": status, "user": user},
                )
            for person, org, count in (
                (first, org_one, 8),
                (second, org_one, 1),
                (different_tenant, org_two, 1),
                (archived, org_one, 1),
            ):
                for i in range(count):
                    await session.execute(
                        text(
                            "INSERT INTO consultant_evidence_index "
                            "(organization_id, person_id, evidence_type, evidence_id, "
                            "content, content_hash, embedding_model, embedding) "
                            "VALUES (:org, :person, 'project', :eid, :content, "
                            "'test', :model, CAST(:vector AS vector))"
                        ),
                        {
                            "org": org, "person": person, "eid": uuid.uuid4(),
                            "content": "soil testing laboratory" if i == 0 else "unrelated",
                            "model": "test" if i == 0 else None,
                            "vector": vec if i == 0 else None,
                        },
                    )
            await session.commit()
            retriever = ConsultantEvidenceRetriever(session, org_one)
            hits = await retriever.retrieve("soil testing", limit=5)
            assert {hit.person_id for hit in hits} == {first, second}
            assert len(hits) == 2
            vector_hits = await retriever.retrieve(
                "soil testing", limit=5, query_embedding=[1.0] + [0.0] * 1535
            )
            assert {hit.person_id for hit in vector_hits} == {first, second}
            await session.rollback()
            # Org isolation and archived exclusion must also hold on the pure
            # semantic path, with no lexical terms.
            semantic_hits = await retriever.retrieve(
                "", limit=5, query_embedding=[1.0] + [0.0] * 1535
            )
            assert {hit.person_id for hit in semantic_hits} == {first, second}
    finally:
        await engine.dispose()
