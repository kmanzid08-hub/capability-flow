# Multi-tenancy and isolation

Tenant isolation is an application and query invariant, not a frontend filter.

- Browser-supplied `X-Organization-ID` is only a selector. It is accepted after proving an active membership for the authenticated user.
- Every tenant-owned record includes `organization_id`.
- A `PersonRepository` cannot be created without organization context.
- Get, list, update, and archive operations filter by organization. Cross-tenant UUID probes return 404.
- Mutation authorization is evaluated from the trusted membership role.
- Integration tests create two tenants and prove that the second cannot read, modify, or archive the first tenant's Person.

Production hardening should add PostgreSQL row-level security as defense in depth, request/audit logging, token revocation or short-lived access plus refresh rotation, rate limiting, security monitoring, and automated isolation tests for every new tenant-owned model. Application filtering remains required even with RLS.

