# Architecture

Capability Flow uses a modular monorepo. The backend is divided into HTTP routing, validation schemas, application services, tenant-aware repositories, persistence models, and security utilities. Routes translate HTTP concerns; services own use cases and transactions; repositories constrain database access.

The React client is a separate Vite application. It uses route protection for navigation convenience, TanStack Query for server state, React Hook Form and Zod for input validation, and one API adapter that attaches credentials and the selected organization. Backend authorization remains authoritative.

## Request flow

1. The bearer token identifies a globally unique active user.
2. `X-Organization-ID` selects one of that user's active memberships. The header may be omitted only when exactly one active membership exists.
3. The membership dependency verifies organization status and exposes trusted organization context.
4. tenant-owned services construct repositories with that context.
5. Person queries include `organization_id`; a UUID alone is never a lookup boundary.

The registration use case creates its organization, first user, and owner membership in one transaction. People are archived by status instead of physically deleted.

## Durable AI jobs

Long-running AI work is admitted through the `ai_jobs` PostgreSQL queue instead of being owned by a browser request or an in-memory task map. The API creates or reuses one active job per tenant/entity and returns immediately. Worker slots claim jobs with database row locks, maintain renewable leases/heartbeats, and retry transient failures with bounded exponential backoff.

The first production stage runs worker slots inside the API service so document analysis can continue to use the service's existing storage mount. Queue state is durable: if Render restarts the process, an expired lease is reclaimed and the source analysis resumes. The worker boundary is intentionally isolated so it can later be moved to a dedicated service once all document storage is shared/object-backed.

AI admission has three limits: global worker concurrency, per-organization running concurrency, and per-user running concurrency. A separate per-organization active-queue cap prevents one tenant from consuming unbounded database/AI capacity. These limits are server-side and do not rely on frontend behavior.
