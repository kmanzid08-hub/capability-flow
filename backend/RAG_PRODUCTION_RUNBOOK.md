# Consultant RAG — Production rollout and rollback

## Scope and safety
This release builds an organization-scoped, evidence-level pgvector index for consultant
skills, education, certifications, work experience and projects. It compares hybrid
retrieval with the **existing** deterministic matcher and logs per-role recall.
It **does not** replace or change current consultant rankings, mandatory-qualification
checks, team selection, or the opportunity extraction pipeline.

The feature is disabled by default. Set `RAG_SHADOW_ENABLED=true` only after
confirming the migration, health checks and provider configuration. Safe rollback is
`RAG_SHADOW_ENABLED=false`; do not drop indexed evidence during rollback.

## Database deployment
- Apply Alembic revision `20261118_0014` after taking a normal database backup.
- Requires Postgres with the `vector` extension. Neon supports `CREATE EXTENSION
  IF NOT EXISTS vector` and the migration does that automatically.
- The evidence table is scoped by organization and person. The migration does not
  modify existing people, matching, or opportunity tables.
- Run the disposable pgvector test, full backend pytest suite, Ruff, and mypy
  before merging. The GitHub Action `RAG shadow validation` includes these checks.

## Provider configuration
- `RAG_SHADOW_ENABLED=false` (initial production deploy).
- `RAG_SHADOW_LIMIT=100` (up to 500).
- `RAG_EMBEDDING_PROVIDER=gemini` uses existing `GEMINI_API_KEY` by default;
  provider `openai` requires a distinct `RAG_EMBEDDING_API_KEY`.
- `RAG_EMBEDDING_MODEL=gemini-embedding-001` for Gemini or
  `text-embedding-3-small` for OpenAI.
- `RAG_EMBEDDING_BATCH_SIZE=8` and
  `RAG_EMBEDDING_MAX_BATCHES_PER_ANALYSIS=2` bound provider traffic and cost.
  The index initially contains text only; embeddings are created incrementally.
- All vectors have 1536 dimensions. Retrieval refuses to compare mismatched models.
- Provider errors/timeouts degrade to lexical shadow rather than failing core matching.

## Progressive rollout
1. Deploy with the feature disabled. Verify `/api/v1/health` returns 200, and
   that the production Alembic migration completes.
2. Enable shadow mode. Analyze a small existing test tender with known consultant
   evidence. Ensure logs contain `RAG shadow evidence index refreshed` and
   `RAG shadow comparison`, with no unhandled exceptions or user-facing changes.
3. Monitor `recall=X/Y` per role and flag missing baseline top candidates.
   Validate them manually against their source evidence; baseline top-25 recall
   alone is **not** proof of true qualification recall.
4. Measure latency and API quota/cost before increasing batch size.
5. Do not switch the active candidate set to RAG until benchmark recall, tenant
   isolation, stale-record handling, and false exclusion rates are satisfactory.

## Rollback
- Set `RAG_SHADOW_ENABLED=false` in Render and redeploy.
- No data or schema rollback is necessary. Existing deterministic matching continues
  throughout rollout. If new application startup or migration fails, revert the
  release commit and redeploy the previous successful commit.
- Never expose CV text, contact information, embedding keys, or database URLs in logs.
