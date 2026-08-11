# Codex working guide

## Scope and language

Use neutral domain language: Person, Resource, Skill, Qualification, Experience, Opportunity, Requirement, and Match. Never rename Person to Consultant or make the product specific to one industry. Do not implement roadmap features before their phase is requested.

## Backend conventions

- Python 3.12, full type annotations, Ruff formatting, strict mypy.
- Keep routes thin. Put use cases in services and persistence in repositories.
- Every tenant-owned table has a non-null `organization_id`.
- Never accept organization ownership from a request body. Derive it from the authenticated active membership.
- Require organization context in tenant repository constructors and include it in every query.
- Use UUID keys, timezone-aware UTC timestamps, transactional multi-record use cases, and Alembic migrations.
- Return 404 for inaccessible tenant records to avoid disclosing their existence.
- Add cross-tenant read and mutation tests for every tenant-owned resource.

## Frontend conventions

- TypeScript strict mode and functional React components.
- TanStack Query owns server state; React Hook Form plus Zod owns forms.
- Keep API transport centralized. Frontend route guards improve UX but never replace backend authorization.
- Use accessible labels, focus states, responsive layouts, and neutral wording.

## Definition of done

Run backend Ruff, mypy, and pytest checks plus frontend ESLint, Vitest, and production build. Update the architecture and model documentation when an invariant changes. Never report a check as passing unless it was actually run.

