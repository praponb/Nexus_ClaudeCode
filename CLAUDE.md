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

- Full history, current accounts, and the operations runbook:
  `SESSION-2026-08-28-SECURITY.md`.
- Backend gates: `./scripts/check.sh` (six gates). It falls back to a one-off
  dev-stage container automatically, because the deployed image is the
  production target and carries no ruff/mypy/pytest.
- Frontend gates: `cd frontend && npm run lint && npm run typecheck && npm run test`.
- **Editing `compose.yaml` triggers an unattended `docker compose up -d` within
  5 minutes** — a launchd watchdog polls on that interval. A half-finished edit
  can take the site down. Check
  `~/Library/Logs/inventory-stack-autostart.log` afterwards.
- The real root `.env` is gitignored, so production configuration is not in git
  and a regression there leaves no trace. Verify the *running* config
  (`docker compose exec backend python -c "...settings.DEBUG"`), not the repo.

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
