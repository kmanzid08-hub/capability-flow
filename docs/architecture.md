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

