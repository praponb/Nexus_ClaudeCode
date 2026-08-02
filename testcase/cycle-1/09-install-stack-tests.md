# Cycle 1 — Installation, Stack Quality Gates, and Hygiene Tests (STK-1…STK-6; NFR-004 smoke; NFR-010)

These tests run primarily via allowlisted commands in the execute phase.

---

### TC-STK-1-01 — Repository structure and lockfiles
- **requirement_ids:** STK-1, NFR-010
- **priority:** High | **type:** Static | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Inspect repo root: `frontend/`, `backend/`, `scripts/`, `testcase/`, `requirements/`, `compose.yaml`, `.env.example`, `README.md`, `.gitignore`; verify `frontend/pnpm-lock.yaml` and `backend/uv.lock` (or documented alternative) are committed.
- **expected_result:** Structure matches stack §5; lockfiles present; no generated artifacts (node_modules, caches, media, local DBs) tracked.
- **status:** NOT_RUN

### TC-STK-1-02 — Secrets hygiene
- **requirement_ids:** STK-5, NFR-007
- **priority:** Critical | **type:** Security/Static | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Verify `.env` is in `.gitignore` and not committed; scan tracked files for obvious secrets (private keys, tokens, passwords beyond documented dev-only seed credentials); confirm `.env.example` contains placeholders only (`replace-me`), no real values.
- **expected_result:** No secrets in source control; `.env.example` matches stack §12 shape; any dev seed passwords documented only in README and clearly marked local-only.
- **status:** NOT_RUN

### TC-STK-2-01 — Frontend quality commands pass
- **requirement_ids:** STK-2, NFR-010
- **priority:** Critical | **type:** Build/Test | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Run, in `frontend/`: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`.
- **expected_result:** All four exit 0; build produces production output; no TypeScript strict errors; test suite passes with meaningful tests (not empty). Evidence: captured command output.
- **status:** NOT_RUN

### TC-STK-3-01 — Backend quality commands pass
- **requirement_ids:** STK-3, NFR-010
- **priority:** Critical | **type:** Build/Test | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Run, in `backend/`: `ruff format --check`, `ruff check`, `mypy`, `python manage.py makemigrations --check --dry-run`, `python manage.py check --deploy` (with safe CI settings), `pytest`.
- **expected_result:** All exit 0; no missing migrations; deploy check findings resolved or explicitly documented; pytest suite passes including API/permission/concurrency/audit tests per cycle plan. Evidence: captured output.
- **status:** NOT_RUN

### TC-STK-4-01 — Setup scripts reproducible and idempotent
- **requirement_ids:** STK-4, NFR-010
- **priority:** Critical | **type:** Installation | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** From a clean state: `./scripts/dev-up.sh`; `./scripts/migrate.sh`; `./scripts/seed-dev.sh`; then re-run `migrate.sh` and `seed-dev.sh`; finally `./scripts/dev-down.sh` and `dev-up.sh` again.
- **expected_result:** Fresh run yields working app (frontend :3000, backend :8000); scripts stop on error, print environment banner, are safe to re-run (migrations no-op, seed idempotent or clearly documented behavior); down/up cycle clean.
- **status:** NOT_RUN

### TC-STK-4-02 — Compose services healthy
- **requirement_ids:** STK-4, NFR-005
- **priority:** High | **type:** Installation | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** After dev-up: check service status for `frontend`, `backend`, `postgres` (and `redis`/worker placeholders if wired); `GET localhost:8000/api/v1/health/ready`; load `localhost:3000`.
- **expected_result:** Required services running/healthy; readiness 200; sign-in page renders; browser never connects directly to postgres/redis.
- **status:** NOT_RUN

### TC-STK-5-01 — Production settings fail fast (D-13)
- **requirement_ids:** STK-5, NFR-007, design D-13
- **priority:** High | **type:** Security/Config | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Run backend startup/checks with `DJANGO_SETTINGS_MODULE=config.settings.production` and missing/placeholder env (no secret key, `DEBUG` unset/true, empty allowed hosts).
- **expected_result:** Startup/check fails fast with clear errors identifying missing/insecure settings; `DEBUG=false` enforced; never silently starts insecure.
- **status:** NOT_RUN

### TC-STK-5-02 — Local auth gated outside production
- **requirement_ids:** STK-5, NFR-007, design D-01
- **priority:** High | **type:** Security/Config | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Attempt to enable local auth while `APP_ENV=production` without `LOCAL_AUTH_ENABLED=true` (config-level test or startup check); confirm local auth works in local env.
- **expected_result:** Production + local-auth-without-override fails startup (or logs loud documented warning per design) ; local dev login works; behavior matches design §12.
- **status:** NOT_RUN

### TC-STK-6-01 — Documentation deliverables present
- **requirement_ids:** STK-6, NFR-010
- **priority:** Medium | **type:** Docs | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Check for root README (setup + commands), env reference, OpenAPI docs location, `ASSUMPTIONS.md`/ADRs if any version deviations occurred (A-06).
- **expected_result:** Documents exist and match reality (commands work as written); any stack-version deviations recorded with ADR.
- **status:** NOT_RUN

### TC-STK-6-02 — E2E test command available
- **requirement_ids:** STK-2, STK-6
- **priority:** Medium | **type:** Build/Test | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Run `pnpm test:e2e` in `frontend/` (against compose stack if required).
- **expected_result:** Playwright suite executes (sign-in, create asset, search+open detail, stale-version conflict messaging per cycle plan); passes, or failures produce defects. If the environment cannot run browsers, mark BLOCKED and run manual equivalents of TC-J6/TC-J1.
- **status:** NOT_RUN

---

### TC-NFR-004-01 — Performance smoke: dashboard
- **requirement_ids:** NFR-004
- **priority:** Medium | **type:** Performance smoke | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** With seed volume (~200 assets), measure `GET /api/v1/dashboard/summary` server response time over 10 requests (authenticated), and page load of `/` (rough, via timing logs).
- **expected_result:** API p95 well under 3s target at this volume (record actual numbers as evidence; flag if >1s server-side at 200 assets — a scalability risk for 100k).
- **status:** NOT_RUN

### TC-NFR-004-02 — Performance smoke: search and detail
- **requirement_ids:** NFR-004
- **priority:** Medium | **type:** Performance smoke | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** Measure `GET /api/v1/assets?page=1` (filtered and unfiltered), `GET /api/v1/search/assets?q=...`, and `GET /api/v1/assets/{uuid}` over 10 requests each; note query counts if backend exposes them (assertNumQueries coverage in backend tests is evidence for N+1 control).
- **expected_result:** Responses far below the 2s p95 targets at seed volume; backend test suite includes N+1 assertions on hot endpoints (verify test exists; if absent, defect/recommendation).
- **status:** NOT_RUN

### TC-NFR-010-01 — Migrations authoritative and clean
- **requirement_ids:** NFR-010, STK-3
- **priority:** High | **type:** Data | **automation_status:** AUTOMATED_CANDIDATE
- **steps:** From empty DB, run migrations; verify schema objects exist (tables, partial unique index on active assignment, unique asset tag); run `makemigrations --check --dry-run` (covered in TC-STK-3-01) to confirm no model drift.
- **expected_result:** Schema builds from zero via migrations only; key constraints present (unique tag; partial unique one-active-assignment); no drift.
- **status:** NOT_RUN
