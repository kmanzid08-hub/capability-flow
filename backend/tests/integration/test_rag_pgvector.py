"""Database-backed smoke tests for pgvector RAG retrieval.

Run with RAG_TEST_DATABASE_URL pointed at disposable pgvector PostgreSQL.
"""
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.consultant_retrieval import ConsultantEvidenceRetriever


@pytest.mark.asyncio
async def test_tenant_scope_person_rank_and_vector_retrieval() -> None:
    database_url = os.getenv("RAG_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Requires disposable RAG_TEST_DATABASE_URL")
    engine = create_async_engine(database_url)
    org_one, org_two = uuid.uuid4(), uuid.uuid4()
    person_one, person_two, other_person, archived_person = (uuid.uuid4() for _ in range(4))
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(text("CREATE TEMP TABLE rag_people (id uuid PRIMARY KEY, organization_id uuid NOT NULL, profile_status text NOT NULL) ON COMMIT PRESERVE ROWS"))
            await conn.execute(text(
                "CREATE TEMP TABLE rag_evidence ("
                "person_id uuid NOT NULL, organization_id uuid NOT NULL, "
                "evidence_type text NOT NULL, evidence_id uuid NOT NULL, "
                "content text NOT NULL, embedding vector(1536), "
                "PRIMARY KEY(organization_id, person_id, evidence_type, evidence_id)) "
                "ON COMMIT PRESERVE ROWS"
            ))
            for person, org, status in (
                (person_one, org_one, "ACTIVE"),
                (person_two, org_one, "ACTIVE"),
                (other_person, org_two, "ACTIVE"),
                (archived_person, org_one, "ARCHIVED"),
            ):
                await conn.execute(text(
                    "INSERT INTO rag_people VALUES (:person, :org, :status)"
                ), {"person": person, "org": org, "status": status})
            for person, org, content, repeat in (
                (person_one, org_one, "soil testing laboratory", 8),
                (person_two, org_one, "soil testing laboratory", 1),
                (other_person, org_two, "soil testing laboratory", 1),
                (archived_person, org_one, "soil testing laboratory", 1),
            ):
                for i in range(repeat):
                    await conn.execute(text(
                        "INSERT INTO rag_evidence VALUES "
                        "(:person, :org, 'project', :evidence, :content, "
                        "CAST(:embedding AS vector))"
                    ), {
                        "person": person, "org": org, "evidence": uuid.uuid4(),
                        "content": content if i == 0 else "unrelated",
                        "embedding": "[" + ",".join(
                            ["1.0"] + ["0.0"] * 1535
                        ) + "]" if i == 0 else None,
                    })

        # Temporary tables are connection-local. The test uses a dedicated
        # connection and remaps the production table names through a temp view.
        async with engine.connect() as conn:
            async with conn.begin():
                await conn.execute(text(
                    "CREATE TEMP VIEW consultant_evidence_index AS "
                    "SELECT * FROM rag_evidence"
                ))
                await conn.execute(text("CREATE TEMP VIEW people AS SELECT * FROM rag_people"))
            # A single-connection session preserves the temp views.
            maker = async_sessionmaker(bind=conn, expire_on_commit=False)
            async with maker() as session:
                retriever = ConsultantEvidenceRetriever(session, org_one)
                hits = await retriever.retrieve("soil testing", limit=5)
                assert {h.person_id for h in hits} == {person_one, person_two}
                assert len(hits) == 2
                vector = [1.0] + [0.0] * 1535
                hits = await retriever.retrieve(
                    "soil testing", limit=5, query_embedding=vector
                )
                assert {h.person_id for h in hits} == {person_one, person_two}
    finally:
        await engine.dispose()
