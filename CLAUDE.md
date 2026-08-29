# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

`agentic_builder`: a Python + Google ADK orchestrator running four LLM
agents (Team Lead, Frontend, Backend, QA) through an explicit three-cycle
design/implement/QA state machine, turning Markdown requirements into a
generated full-stack web app. The full build spec is `ClaudeCode-prompt.md`
(historical -- the project it describes is now built; treat the current
source tree and `README.md`/`ASSUMPTIONS.md` as authoritative over it for
anything that has since been decided or discovered).

## Commands

```bash
pip install -e '.[dev]'          # editable install with dev deps
ruff check .                     # lint
ruff format .                    # format
mypy src                         # type check
pytest                           # full test suite (offline, MODEL_PROVIDER=fake)
python -m agentic_builder validate --input-dir requirements
python -m agentic_builder run --input-dir requirements --workspace . --verbose
```

All four quality gates (`ruff check`, `ruff format --check`, `mypy src`,
`pytest`) must pass before considering a change done. The test suite runs
entirely offline against the `FakeLlm` double -- no credentials needed.

## The generated app is live and public

`backend/` + `frontend/` are not just build output any more: they are deployed
at <https://inventory.praponb.com>, reachable by anyone, with no Cloudflare
Access in front. **Changes here reach the public internet.** The Django login is
the only gate.

**Production moved off this Mac on 2026-08-29.** It now runs on an Ubuntu 26.04
LTS server: `prapon@192.168.1.49`, deployed at `~/inventory`, serving the same
Cloudflare Tunnel as before, now as a systemd `cloudflared` service. The MacBook is a **cold
standby** — containers stopped, volumes intact, both LaunchAgents unloaded. Full
procedure and rollback: `DEPLOY-UBUNTU.md`.

- **Open issues and anything needing action: `SESSION-2026-08-29-ISSUES.md`.**
- Full history, current accounts, and the operations runbook:
  `SESSION-2026-08-28-SECURITY.md`.
- **Code reaches production via `scripts/sync-to-server.sh` (rsync), not git.**
  The server has no remote and no history. The script therefore **refuses a dirty
  working tree** (`--allow-dirty` to override) and stamps a `DEPLOYED_COMMIT`
  file into the transfer, so the server records the SHA it is running:
  `ssh prapon@192.168.1.49 'cat ~/inventory/DEPLOYED_COMMIT'`.
- **Deploying means: sync, then rebuild on the server.**
  `./scripts/sync-to-server.sh` then, over ssh,
  `cd ~/inventory && ./scripts/backup.sh && docker compose build && docker compose up -d && ./scripts/migrate.sh`.
- Backend gates: `./scripts/check.sh` (six gates). It falls back to a one-off
  dev-stage container automatically, because the deployed image is the
  production target and carries no ruff/mypy/pytest. Gates run on the **Mac**;
  starting the local stack for them no longer affects production.
- Frontend gates: `cd frontend && npm run lint && npm run typecheck && npm run test`.
- The real root `.env` is gitignored, so production configuration is not in git
  and a regression there leaves no trace. Verify the *running* config on the
  server, not the repo. It is also a *merged* file: it holds the orchestrator's
  `MODEL_*` / `GEMINI_API_KEY` secrets next to the web app's Django settings.
  Never copy it wholesale to an app host — `scripts/export-app-env.sh` extracts
  the app subset by allowlist, and is what wrote the server's `.env`.
- **The server also hosts `chatbot.praponb.com`** (containers `twin`,
  `twin-tunnel`, a separate compose project in `~/twin`). Never
  `docker system prune -a` or bulk-stop containers there — it would take an
  unrelated public site down.
- Two pre-existing defects were found during the migration; both are now
  resolved (2026-08-30). Attachment uploads failed with `PermissionError`
  because `/app/media` did not exist in the image, so Docker created the volume
  mount point root-owned — fixed in `backend/Dockerfile` and deployed.
  `verify_chain()` still returns `False`, but it is **explained and benign**:
  `AuditEvent.actor` is `SET_NULL` and the payload hashes `actor.uuid`, so
  deleting a user invalidates that user's rows while leaving the chain links
  intact. Diagnose with `python manage.py audit_chain_report` (read-only).
  **Never run `reseal_chain()`** — it hides the discrepancy and destroys the
  evidence. Details: `SESSION-2026-08-29-ISSUES.md` §2.

### On the standby Mac

- Both LaunchAgents (`com.nexus.inventory-autostart`,
  `com.praponb.inventory.backup`) are **unloaded**. The 5-minute watchdog that
  made editing `compose.yaml` dangerous is therefore inert — but reload it and
  that hazard returns.
- The tunnel LaunchDaemon (`/Library/LaunchDaemons/com.cloudflare.cloudflared.plist`)
  is **booted out**. Restoring it is the rollback step, and must never run while
  the server's tunnel is up — one tunnel, one host, or Cloudflare load-balances
  across two diverging databases.
- `jobs4dent` and `twin` LaunchAgents were `launchctl disable`d on 2026-08-29.
  Renaming a plist does **not** disable it; only `launchctl disable` persists.

## Ownership boundaries (enforced in code, not just convention)

| Owner | Path |
|---|---|
| Team Lead | `detail-design-specification.md`, `runs/<id>/cycle-*/cycle-plan.md` |
| Frontend agent | `frontend/` |
| Backend agent | `backend/`, `scripts/` |
| QA agent | `testcase/`, `runs/<id>/cycle-*/qa-execution-report.md`, `defects.json` |
| Orchestrator | `runs/<id>/state.json`, `events.jsonl`, `traceability.json`, `final-report.md` |

`tools/owned_writers.py` rejects any path outside an agent's allowed
prefixes at runtime -- don't rely on "only this agent has the tool wired
up" as the sole guard when adding new write paths.

## Inspect the installed ADK API before guessing

`google-adk` and `litellm` move fast; do not assume method signatures,
field names, or exception types from memory or from this file. Before
touching `models/`, `agents/`, or `orchestrator.py`, check the installed
package directly, e.g.:

```bash
python -c "from google.adk.agents import LlmAgent; print(list(LlmAgent.model_fields))"
python -c "import inspect, google.adk.models.base_llm as m; print(inspect.getsource(m.BaseLlm))"
```

This project was built by inspecting google-adk 2.6.1 / litellm 1.94.1
directly (see `ASSUMPTIONS.md`) rather than assuming an API shape --
keep doing that when a version bump changes something.

## Requirements vs. fixtures

- `requirements/` -- real, user-authored input. Ships empty; never write
  example content here.
- `tests/fixtures/` -- example/adversarial requirement sets used only by
  the automated test suite. Never read by default CLI invocation.

## Model configuration

Default model is `kimi-k3` (real Moonshot AI model, routed through
litellm's built-in `moonshot` provider). Never silently substitute a
different model if `kimi-k3` access fails -- that is an explicit spec
requirement; fail with `ConfigError`/`ModelResolutionError` instead. See
`config.py` and `models/provider.py`.

## Security invariants (do not weaken without discussion)

- Requirement/workspace file content read by tools is always wrapped in
  `BEGIN/END UNTRUSTED DATA` delimiters (`tools/workspace.wrap_untrusted`)
  and never concatenated into an agent's `instruction`/`global_instruction`.
- Subprocess execution only ever goes through
  `tools/subprocess_runner.run_allowlisted_command` with a fixed
  `command_key` from `ALLOWLIST` -- never a raw string, never `shell=True`.
- All file writes go through `tools/workspace.resolve_within` (path
  traversal guard) and `events.atomic_write_text`/`atomic_write_json`.
- Secrets are masked via `config.mask_secrets` everywhere text is logged,
  persisted to `events.jsonl`, or shown in CLI error output.

Invariants for the deployed app (`backend/`) -- same rule, do not weaken
without discussion:

- Client identity for throttling and audit comes from
  `apps/core/client_ip.py`, which trusts one configured header then
  `REMOTE_ADDR`. **Never key on `X-Forwarded-For`** -- it is caller-supplied,
  so rotating it buys a fresh throttle bucket per request, and it once reached
  a Postgres `inet` column unvalidated (an unauthenticated 500).
- Throttle counters must live in a *shared* cache. Django's default
  `LocMemCache` is per-process: under `gunicorn --workers 3` it multiplies
  every configured rate by three and resets on each deploy.
- Dev throttle ceilings belong in `local.py`/`test.py` only. A permissive rate
  in `base.py` silently disables protection in production *and* makes those
  overrides look like no-ops -- which is exactly how it went unnoticed before.
- `POST /auth/login/` must not establish a session for an MFA-required role
  until the second factor is satisfied.
- The public `demo` account stays exempt from per-account lockout; locking a
  shared published account denies every visitor at once.
