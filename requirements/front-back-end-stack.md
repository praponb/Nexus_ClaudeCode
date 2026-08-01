# Frontend, Backend, and Database Technology Stack

## 1. Document Information

- **Application:** Asset Inventory Web Application
- **Document:** Frontend, Backend, and Database Stack
- **Version:** 1.0
- **Status:** Initial technical constraints
- **Related documents:** `specification.md`, `layout.md`, and `detail-design-specification.md`

## 2. Purpose

This document defines the required technology stack and engineering constraints for the Asset Inventory Web Application. The implementation must use **Nuxt.js** for the frontend, **Django** for the backend, and **PostgreSQL** for persistent data storage.

This document defines technology choices rather than detailed business behavior. Functional requirements remain governed by `specification.md`, visual and interaction requirements by `layout.md`, and the final implementation contracts by `detail-design-specification.md`.

## 3. Architecture Summary

The application must use a separated web-client and API architecture:

```text
User browser
    |
    | HTTPS
    v
Nuxt frontend
    |
    | Versioned JSON REST API over HTTPS
    v
Django + Django REST Framework backend
    |
    | Django ORM and PostgreSQL driver
    v
PostgreSQL database
```

Supporting production services may include:

- Redis for cache, distributed locks, rate-limit state, and background-job coordination
- Celery for asynchronous and scheduled jobs
- S3-compatible object storage for asset images and attachments
- Reverse proxy or ingress controller for TLS termination and routing
- SMTP or an approved email provider for notifications
- OpenID Connect identity provider for production single sign-on

The browser must never connect directly to PostgreSQL, Redis, Celery, or object storage using privileged credentials.

## 4. Required Stack Baseline

Use supported, production-ready releases available when implementation begins. Pin exact dependency versions in lock files and container images after compatibility and security testing.

Recommended baseline for this project:

- **Frontend framework:** Nuxt 4 with Vue 3 and TypeScript
- **Frontend runtime:** Current active Node.js LTS release supported by the selected Nuxt version
- **Package manager:** `pnpm` with a committed `pnpm-lock.yaml`
- **Backend framework:** Django 6.0
- **API framework:** Django REST Framework
- **Backend language:** Python 3.12 or newer version supported by the selected Django release and dependencies
- **Dependency management:** `uv` with a committed lock file, or another reproducible Python lock workflow if project constraints require it
- **Database:** PostgreSQL 18, using the current supported minor release
- **PostgreSQL driver:** Psycopg 3
- **Development orchestration:** Docker Compose

Version policy:

1. Do not use alpha, beta, release-candidate, nightly, or end-of-life versions in production.
2. Use the newest security-patched minor release within the selected major-version line.
3. Verify compatibility among Nuxt, Node.js, Django, Django REST Framework, Python, Psycopg, PostgreSQL, and all supporting packages before pinning.
4. If an approved deployment platform does not yet support the recommended major version, use the newest mutually supported stable major version and record the reason in `ASSUMPTIONS.md` and the architecture decision record.
5. Automated dependency and container scanning must run in CI.

## 5. Repository Structure

The generated application must use the following high-level structure:

```text
.
├── frontend/                   # Nuxt application
├── backend/                    # Django application
├── scripts/                    # Local setup, CI, migration, and operations helpers
├── testcase/                   # Cross-system QA cases, evidence, and reports
├── requirements/               # User-authored Markdown inputs
├── detail-design-specification.md
├── compose.yaml
├── .env.example
├── README.md
└── .gitignore
```

Rules:

- Frontend source and frontend-specific tests belong under `frontend/`.
- Backend source, migrations, and backend-specific tests belong under `backend/`.
- End-to-end and cross-system QA assets belong under `testcase/`.
- Shared scripts must work from the repository root and must not contain secrets.
- Generated artifacts, uploaded files, local databases, caches, coverage output, and secrets must be excluded from source control.

## 6. Frontend Stack

### 6.1 Core Technologies

The frontend must use:

- Nuxt 4
- Vue 3 Composition API
- TypeScript with strict type checking
- Vue Single-File Components
- Nuxt file-based routing
- Vite through the standard Nuxt toolchain
- `pnpm` for package installation and scripts

New frontend code must use `<script setup lang="ts">` unless a documented technical reason requires another style.

### 6.2 Rendering Strategy

Use Nuxt's hybrid rendering capabilities deliberately:

- Authenticated, highly interactive inventory pages may use client-side rendering where this simplifies secure session-dependent behavior.
- The application shell, sign-in entry, help content, and suitable read-only pages may use server-side rendering.
- Do not expose confidential API responses, access tokens, or user-specific inventory data through public payload caching or static generation.
- Document route rendering and caching decisions in the detailed design.

### 6.3 UI and Styling

- Use **Nuxt UI** as the preferred accessible component foundation.
- Use Tailwind CSS through the supported Nuxt UI integration for layout and design tokens.
- Create application-specific components for asset workflows rather than tightly coupling business logic to generic UI components.
- Use a centralized theme for colors, typography, spacing, borders, focus states, breakpoints, and status semantics.
- Do not communicate status by color alone.
- Target WCAG 2.2 Level AA as required by `specification.md`.
- The final component and styling choices must conform to `layout.md`.

### 6.4 State Management

Use the smallest appropriate state mechanism:

- Use Nuxt `useState` and composables for simple application state.
- Use Pinia only for genuinely shared or complex client-side state.
- Treat the backend as the source of truth for asset, assignment, maintenance, stocktake, and audit data.
- Do not duplicate server data across unrelated stores.
- Store filters and pagination in URL query parameters when users should be able to bookmark or share a view.

### 6.5 API Client

- Create a typed API-client layer around Nuxt `$fetch` or `useFetch`.
- Use one configurable backend base URL.
- Centralize authentication handling, correlation IDs, validation-error mapping, timeout behavior, and safe retry rules.
- Generate TypeScript API types or a client from the backend OpenAPI document when practical.
- Do not call backend endpoints directly from arbitrary presentation components.
- Do not retry non-idempotent operations unless the request uses an approved idempotency mechanism.
- Do not display raw backend exceptions to users.

### 6.6 Authentication in the Browser

Preferred production authentication is organizational single sign-on using OpenID Connect.

- Prefer secure, `HttpOnly`, `Secure`, appropriately scoped cookies for browser sessions.
- Do not store long-lived access or refresh tokens in `localStorage`.
- Protect cookie-authenticated unsafe requests with CSRF controls.
- Refresh or session-renewal behavior must be centralized.
- The UI may hide inaccessible actions for usability, but the backend remains responsible for authorization.
- Route middleware may improve navigation behavior but must not be treated as a security boundary.

### 6.7 Frontend Functional Areas

Organize the frontend by business feature, including:

- Authentication and user profile
- Dashboard
- Asset search and asset register
- Asset detail and activity history
- Asset creation and editing
- Assignment, transfer, return, reservation, and checkout
- Maintenance and warranty
- Stocktake and scanning
- Import and export
- Reports and saved views
- Notifications and approvals
- Reference-data and user administration

### 6.8 Frontend Testing

Use:

- Vitest for unit tests
- Vue Test Utils and Nuxt test utilities for component and Nuxt-context tests
- Playwright for end-to-end and browser tests
- Automated accessibility checks, supplemented by keyboard and screen-reader-oriented manual checks

Required frontend quality commands must cover:

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Add a separate end-to-end command, such as:

```bash
pnpm test:e2e
```

The exact scripts must be documented in `frontend/package.json` and the root `README.md`.

### 6.9 Frontend Code Quality

- Use ESLint with Nuxt-supported configuration.
- Use formatting rules consistently and enforce them in CI.
- Avoid `any`; document unavoidable exceptions.
- Keep components focused and move reusable behavior into typed composables or services.
- Provide loading, empty, success, warning, error, unauthorized, and offline or network-failure states where relevant.
- Lazy-load large optional features when useful, but do not compromise usability.

## 7. Backend Stack

### 7.1 Core Technologies

The backend must use:

- Django 6.0
- Django REST Framework for REST APIs
- Python with type hints
- Psycopg 3 for PostgreSQL connectivity
- Django ORM for normal database access
- Django migrations for all schema changes
- An OpenAPI generation package compatible with the selected Django REST Framework version

Use raw SQL only when justified by measured performance or a database feature that cannot be expressed safely through the ORM. Raw SQL must be parameterized and covered by tests.

### 7.2 Backend Project Organization

Recommended structure:

```text
backend/
├── manage.py
├── pyproject.toml
├── uv.lock
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── test.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── accounts/
│   ├── assets/
│   ├── assignments/
│   ├── maintenance/
│   ├── stocktakes/
│   ├── reporting/
│   ├── notifications/
│   ├── audit/
│   └── reference_data/
└── tests/
```

The final module boundaries must follow the domain model in `detail-design-specification.md`. Avoid one oversized application containing unrelated responsibilities.

### 7.3 API Design

- Expose versioned APIs under `/api/v1/`.
- Use JSON for normal request and response bodies.
- Use predictable resource naming and standard HTTP methods.
- Use UUIDs or another non-sequential public identifier for externally exposed primary resources.
- Define a consistent error envelope with a stable error code, user-safe message, field errors when applicable, and correlation ID.
- Apply server-side filtering, ordering, search, and pagination.
- Set conservative page-size defaults and enforce maximum page sizes.
- Support idempotency keys for retry-sensitive create or transition operations where duplication would be harmful.
- Use optimistic concurrency control for material asset updates, such as a version field or conditional request mechanism.
- Generate and publish an OpenAPI schema.
- Treat the OpenAPI schema as the contract used by frontend development and contract testing.

Example error shape:

```json
{
  "error": {
    "code": "ASSET_STATUS_TRANSITION_INVALID",
    "message": "The asset cannot move from Assigned to Disposed.",
    "field_errors": {},
    "correlation_id": "3eeab8b7-6c83-4dbe-b62b-9dbdb3cb8dab"
  }
}
```

### 7.4 Backend Business Logic

- Keep serializers focused on representation and boundary validation.
- Place multi-record lifecycle behavior in explicit application services or domain services.
- Use database transactions for assignments, transfers, returns, maintenance completion, stocktake reconciliation, retirement, and disposal.
- Enforce critical invariants in backend code and database constraints where practical.
- Every lifecycle transition must produce the required history and audit records atomically.
- Avoid placing important side effects only in model signals because implicit behavior is difficult to test and reason about.

### 7.5 Authentication and Authorization

- Integrate production authentication with the approved OpenID Connect provider where available.
- Support a clearly isolated local-development authentication mode that cannot be enabled accidentally in production.
- Use Django permissions plus explicit object or organizational-scope checks.
- Enforce authorization in every endpoint, including detail, list, export, attachment, reporting, and administrative endpoints.
- Apply field-level restrictions to sensitive financial and personal data.
- Test horizontal and vertical privilege escalation attempts.
- Use Django Admin only for tightly controlled support functions. It is not the primary end-user interface.

### 7.6 Background and Scheduled Work

Use Celery with Redis when asynchronous processing is required for:

- Bulk CSV import
- Large export generation
- Notification delivery
- Warranty and maintenance reminders
- Scheduled data-quality checks
- Report generation
- Attachment post-processing or malware-scan coordination

Requirements:

- Jobs must be idempotent or safely deduplicated.
- Retries must be bounded and use backoff.
- Job status must be persisted and visible to authorized users.
- Failed jobs must include a support-safe error and correlation identifier.
- Do not pass secrets or unnecessarily large payloads through the queue.
- Scheduler choice, such as Celery Beat, must be documented.

### 7.7 File and Attachment Handling

- Store attachment metadata in PostgreSQL.
- Use S3-compatible object storage in production rather than the application container filesystem.
- Use private buckets or containers and time-limited authorized downloads.
- Validate file type, extension, content signature, and size.
- Integrate with an approved malware-scanning service when available.
- Do not trust user-provided filenames or paths.
- Development may use local media storage only through environment-specific settings.

### 7.8 Backend Testing

Use `pytest`, `pytest-django`, and appropriate factories or fixtures.

Required test categories include:

- Domain and service unit tests
- Serializer and validation tests
- API integration tests
- Authentication, permission, and object-scope tests
- Database constraint and migration tests
- OpenAPI contract tests
- Background-job tests
- Import and export tests
- Attachment authorization and validation tests
- Concurrency and transaction tests
- Audit-event completeness tests

Required backend quality commands must cover formatting, linting, type checking, migration checks, tests, and production configuration checks. A representative interface is:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py check --deploy
uv run pytest
```

Production-specific checks may require safe placeholder settings in CI. Never connect CI validation to a production database.

### 7.9 Backend Code Quality

- Use Ruff for linting and formatting.
- Use mypy with compatible Django typing support.
- Use explicit type annotations for public functions and service boundaries.
- Use structured logging with correlation IDs.
- Never return stack traces or confidential settings to API consumers.
- Keep settings environment-specific and validate required production settings at startup.

## 8. PostgreSQL Database

### 8.1 Database Requirements

- PostgreSQL is the only supported production relational database for this application.
- SQLite may be used only for isolated tooling tests that do not exercise PostgreSQL behavior. Normal development and CI integration tests must use PostgreSQL.
- Use UTF-8 encoding and a documented locale and collation strategy.
- Store timestamps as time-zone-aware values and use UTC as the persistence standard.
- Use Django migrations as the authoritative schema history.
- Never modify the production schema manually outside the controlled migration process.

### 8.2 Data Modeling

- Use normalized relational models for assets, assignments, locations, departments, maintenance, stocktakes, approvals, and lifecycle events.
- Use database constraints for uniqueness, required relationships, and valid values where practical.
- Use partial unique constraints where an invariant applies only to active records, such as one active primary assignment per asset.
- Use `JSONField` only for genuinely flexible category-specific attributes or external payload snapshots. Do not place core searchable business fields in unstructured JSON.
- Use explicit through models for relationships that contain dates, status, actor, or other business attributes.
- Preserve historical references by deactivation or archival rather than unsafe deletion.
- Use UUIDs for public identifiers where appropriate; internal keys may follow the final data design.

### 8.3 Indexing and Query Performance

Create indexes based on actual query patterns and explain them in migrations or design records. Expected indexed fields include combinations involving:

- Asset tag
- Serial number
- Category
- Lifecycle status
- Condition
- Custodian
- Department
- Location
- Warranty end date
- Maintenance due date
- Created and modified timestamps
- External system and external identifier

Use PostgreSQL search capabilities, trigram matching, or a dedicated search service only after detailed search requirements and measured needs justify the choice. Avoid unbounded queries and N+1 query patterns.

### 8.4 Transactions and Concurrency

- Use atomic transactions for lifecycle operations that update multiple records.
- Use row locking selectively for operations where concurrent processing can violate an invariant.
- Keep transactions short and avoid network calls inside open database transactions.
- Design background jobs and APIs for retries without duplicate assignment, transfer, stocktake, or audit events.
- Detect stale updates and return an explicit conflict response rather than silently overwriting data.

### 8.5 Database Security

- Use separate database credentials by environment.
- Grant the application account only the permissions it requires.
- Do not expose PostgreSQL publicly.
- Require encrypted database connections in production.
- Store credentials in an approved secret manager or protected environment injection mechanism.
- Do not log connection strings containing credentials.
- Limit and monitor administrative access.
- Consider a separate migration role if required by the deployment security model.

### 8.6 Backup and Recovery

- Use automated, encrypted backups with tested restoration procedures.
- Support point-in-time recovery when required by the approved recovery objectives.
- Document backup retention, recovery point objective, and recovery time objective.
- Test restoration in a controlled non-production environment.
- Backups must include or be coordinated with attachment storage and required encryption keys or configuration.

## 9. Caching and Redis

Redis is optional for the smallest local setup but recommended when using Celery, shared caching, distributed locks, or multi-instance deployment.

- Do not use Redis as the authoritative store for asset inventory records.
- Cache only data whose staleness and invalidation behavior are understood.
- Do not cache permission-sensitive responses under keys that could leak data between users or scopes.
- Apply timeouts to every cache entry unless persistence is explicitly required.
- Use distinct namespaces or databases for cache and Celery concerns where supported.
- Production Redis must require protected network access and authentication or managed-service controls.

## 10. API and Frontend Integration Contract

- Django owns the business rules, authorization decisions, persistence, and canonical validation.
- Nuxt owns presentation, interaction, browser-side validation, and user feedback.
- Browser-side validation improves usability but never replaces backend validation.
- Backend OpenAPI output must be stored or generated reproducibly for frontend typing and contract tests.
- Breaking API changes require a new API version or an approved compatibility and migration plan.
- Dates and times use ISO 8601 strings with time-zone information.
- Currency values must not use binary floating-point representation. Use an agreed decimal string plus ISO currency code.
- List endpoints must use consistent pagination metadata.
- Both applications must propagate or generate correlation IDs for cross-service troubleshooting.

## 11. Security Requirements for the Stack

At minimum:

- HTTPS is mandatory outside local development.
- Configure secure headers and a restrictive Content Security Policy.
- Configure CORS with an explicit allowlist. Never use unrestricted production origins with credentials.
- Use CSRF protection for cookie-authenticated state-changing requests.
- Validate and normalize all untrusted input.
- Escape untrusted output and avoid unsafe HTML rendering.
- Apply rate limiting to authentication, search-intensive, import, export, and other abuse-sensitive endpoints.
- Protect against CSV formula injection in exports.
- Validate uploads and authorize every download.
- Keep Django `DEBUG` disabled in production.
- Restrict allowed hosts and trusted origins.
- Use secret management instead of committed `.env` files.
- Mask personal, financial, credential, and token data in logs.
- Produce an auditable software bill of materials where the delivery platform supports it.

## 12. Configuration and Secrets

Create a `.env.example` containing names and non-secret examples only. Expected settings include:

```dotenv
# Environment
APP_ENV=local
APP_BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000/api/v1

# Django
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=replace-me
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:3000
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:3000

# PostgreSQL
POSTGRES_DB=asset_inventory
POSTGRES_USER=asset_inventory
POSTGRES_PASSWORD=replace-me
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://asset_inventory:replace-me@postgres:5432/asset_inventory

# Redis and Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Object storage
OBJECT_STORAGE_ENDPOINT=
OBJECT_STORAGE_BUCKET=
OBJECT_STORAGE_ACCESS_KEY=
OBJECT_STORAGE_SECRET_KEY=

# Identity provider
OIDC_ISSUER_URL=
OIDC_CLIENT_ID=
OIDC_CLIENT_SECRET=

# Observability and notifications
SENTRY_DSN=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
DEFAULT_FROM_EMAIL=
```

Rules:

- The real `.env` file must be ignored by Git.
- Production settings must fail fast when required values are absent or insecure.
- Frontend runtime configuration must expose only explicitly public values to the browser.
- Values prefixed or treated as public must never include secrets.

## 13. Local Development

Docker Compose should provide:

- `frontend`
- `backend`
- `postgres`
- `redis`
- `celery-worker`
- `celery-beat` when scheduled tasks are enabled
- Optional S3-compatible development storage

The repository must include documented scripts or commands for:

```bash
# Start local services
./scripts/dev-up.sh

# Apply database migrations
./scripts/migrate.sh

# Seed non-sensitive development data
./scripts/seed-dev.sh

# Run all checks and tests
./scripts/check.sh

# Stop local services
./scripts/dev-down.sh
```

Scripts must be safe to rerun, stop on errors, avoid destructive production behavior, and clearly identify the environment they target.

## 14. CI/CD Quality Gates

A change is not releasable unless the pipeline successfully performs the applicable steps:

1. Install dependencies from committed lock files.
2. Check formatting and linting.
3. Run frontend and backend static type checking.
4. Validate Django migrations and detect missing migrations.
5. Run frontend unit and component tests.
6. Run backend unit and PostgreSQL integration tests.
7. Validate the OpenAPI schema and frontend contract compatibility.
8. Build the Nuxt production application.
9. Run Django production deployment checks.
10. Run end-to-end tests against an isolated full stack.
11. Scan source dependencies, lock files, containers, and secrets.
12. Produce test and coverage reports.
13. Build immutable frontend and backend deployment artifacts.
14. Apply deployment and migration controls appropriate to the target environment.

Do not use production credentials or production data in CI.

## 15. Deployment Requirements

- Build frontend and backend into separate, immutable OCI container images.
- Run the Django web application through a production-capable ASGI server compatible with the selected stack.
- Do not use Nuxt or Django development servers in production.
- Run containers as non-root where practical.
- Use health, readiness, and graceful-shutdown behavior.
- Store uploaded files outside ephemeral application containers.
- Keep PostgreSQL and Redis on private networks or managed private endpoints.
- Run database migrations as a controlled release step, not simultaneously from every application replica.
- Use backward-compatible migration sequencing for rolling deployment where required.
- Separate web, worker, and scheduler processes.
- Enable centralized logs, metrics, tracing or correlation, and alerting.

The target hosting platform is intentionally not fixed by this document. The detailed design must define the chosen platform and its networking, scaling, secrets, backup, observability, and rollback approach.

## 16. Observability

Both frontend and backend must support production troubleshooting:

- Structured backend logs
- Frontend error capture without sensitive data
- Request correlation IDs propagated between Nuxt, Django, and background jobs
- Health and readiness endpoints
- Metrics for traffic, latency, failures, database connections, job queues, imports, exports, and notification delivery
- Alerts for sustained error rates, unavailable services, failed scheduled jobs, and resource exhaustion
- Audit logs separated conceptually from diagnostic application logs

Never use diagnostic logs as a substitute for the protected business audit history required by `specification.md`.

## 17. Documentation Requirements

The implementation must include:

- Root `README.md` with setup and common commands
- Frontend and backend development notes
- Environment-variable reference
- Architecture and deployment diagrams
- OpenAPI documentation
- Data model and migration guidance
- Authentication and authorization explanation
- Background-job operation and retry guidance
- Backup and restore procedure
- Troubleshooting guide
- Dependency-update policy
- Architecture decision records for material deviations from this stack

## 18. Prohibited or Discouraged Choices

Unless an approved architecture decision states otherwise:

- Do not replace Nuxt with a different frontend framework.
- Do not replace Django or Django REST Framework with a different backend framework.
- Do not replace PostgreSQL with SQLite, MySQL, MongoDB, or another production database.
- Do not put business-critical authorization only in Nuxt middleware.
- Do not expose Django models directly without an intentional API contract.
- Do not use floating-point fields for monetary values.
- Do not use unstructured JSON for all asset data.
- Do not store secrets in source control.
- Do not use local container filesystems for production attachments.
- Do not run destructive schema or data commands automatically on production startup.
- Do not claim frontend, backend, or end-to-end tests passed unless they were executed and evidence was retained.

## 19. Definition of Done for the Technology Stack

The stack implementation is complete when:

- `frontend/` is a runnable Nuxt 4 TypeScript application.
- `backend/` is a runnable Django 6 REST API application.
- Django connects to PostgreSQL through environment-based configuration.
- Initial migrations can create the schema from an empty database.
- Nuxt communicates only through the documented versioned Django API.
- Authentication, CSRF, CORS, session or token behavior, and authorization are tested.
- OpenAPI documentation and frontend type integration are available.
- Local Docker Compose startup is documented and reproducible.
- Frontend, backend, PostgreSQL integration, and end-to-end tests pass.
- Linting, formatting, type checks, migration checks, production builds, and security scans pass.
- Background jobs and object storage are implemented when required by enabled features.
- No secrets are committed.
- Production deployment, migration, rollback, backup, recovery, and observability procedures are documented.

## 20. Decisions to Finalize in Detailed Design

The Team Lead agent must resolve and document:

1. Exact pinned versions after compatibility verification
2. Target Node.js and Python versions
3. Nuxt rendering and deployment mode by route
4. Nuxt UI theme and detailed component conventions
5. Authentication provider and browser-session pattern
6. Object-storage and malware-scanning providers
7. Redis and Celery deployment requirements
8. API pagination, filtering, error, and idempotency conventions
9. OpenAPI generation and TypeScript client-generation tooling
10. Hosting and container orchestration platform
11. PostgreSQL managed service, sizing, extensions, backup, and recovery settings
12. Observability providers and service-level indicators
13. Email or notification provider
14. Final CI/CD platform and release strategy
15. Whether offline stocktake capability is required

Any deviation from Nuxt, Django, or PostgreSQL requires explicit product-owner approval. Other stack refinements may be made through a documented architecture decision if they preserve the requirements in `specification.md`.
