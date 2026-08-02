# Assumptions

This file records explicit assumptions and judgment calls made while building
`agentic_builder`, per the build spec's instruction to state assumptions and
proceed rather than repeatedly asking for confirmation. Update it whenever an
assumption changes or is resolved.

## Model provider: `kimi-k3`

- `kimi-k3` is a real, currently-shipping Moonshot AI model (confirmed
  against https://platform.kimi.ai/docs/guide/kimi-k3-quickstart at build
  time), served at `https://api.moonshot.ai/v1` via an OpenAI-compatible
  API, authenticated with a Bearer token, official env var
  `MOONSHOT_API_KEY`. `litellm` (a direct dependency of this project, used
  as ADK's model-provider bridge) ships a native `moonshot` provider
  (`litellm.llms.moonshot.chat.transformation.MoonshotChatConfig`) that
  already defaults its API base to that URL and reads
  `MOONSHOT_API_KEY`/`MOONSHOT_API_BASE` if no explicit `api_base`/`api_key`
  is passed. `kimi-k3` itself does **not** appear in litellm's static
  `model_list` cost/context-window metadata table, but that table is not a
  call allowlist — unlisted models under a supported provider prefix are
  still dispatched normally.
- Given this, `MODEL_PROVIDER=moonshot` + `MODEL_NAME=kimi-k3` is a real,
  working default, not a placeholder. `models/provider.py` builds the
  litellm model id as `f"{MODEL_PROVIDER}/{MODEL_NAME}"` when
  `MODEL_PROVIDER` is a known litellm provider prefix, and fails fast with
  an actionable message (pointing at the key-creation URL) if no API key is
  configured for a non-fake provider. It never silently substitutes a
  different model.
- kimi-k3 always runs with thinking mode enabled and fixes
  `temperature=1.0`, `top_p=0.95`, `n=1` server-side; the adapter does not
  send these as overrides. An optional `reasoning_effort` (`low`/`high`/
  `max`) is forwarded only if `MODEL_REASONING_EFFORT` is set.
- No stub/mock kimi-k3 server is vendored as a project component — it's a
  real, reachable model. README documents the real quickstart (create a
  Moonshot account, top up at least $1, create a key at
  platform.kimi.ai/console/api-keys, set `MODEL_API_KEY`).

## Architecture / tooling choices

- **CLI framework**: stdlib `argparse`, not `click` — the spec asks to
  avoid unnecessary dependencies and the CLI surface (6 subcommands) is
  simple enough for stdlib subparsers.
- **Type checker**: `mypy` (with the pydantic plugin), not `pyright` — pure
  pip-installable, no external binary download required.
- **Workspace default**: `--workspace` defaults to `.` (the repository
  root), matching the spec's "Expected Project Structure" tree where
  `frontend/`, `backend/`, `testcase/`, and `detail-design-specification.md`
  live at the repo root. The spec's CLI example (`--workspace
  ./generated-app`) is treated as illustrative of the flag, not a mandated
  default; workspace remains fully configurable either way.
- **`scripts/` ownership**: assigned to the Backend Developer agent. The
  spec's concurrency-rules section does not explicitly assign this
  directory; `scripts/` most often holds build/migration/deploy scripts
  that are backend-shaped, so it was grouped with `backend/`.
- **Parallel-phase execution**: the orchestrator runs Frontend, Backend, and
  QA test-design concurrently via `asyncio.gather` over independent
  `Runner.run_async` invocations, rather than composing them as an ADK
  `ParallelAgent`. This keeps the two-phase QA split explicit: QA test
  *design* runs in parallel with implementation, but QA *execution* is a
  separate step gated on frontend/backend deliverables actually being
  ready, per the spec's workflow section (step 4).
- **`--cycles` override**: the production `run`/`resume` path enforces
  exactly 3 cycles by default. A separate `--dev-cycles N` flag is required
  to run a non-default cycle count, so the "must enforce exactly three
  cycles" requirement can't be silently bypassed by a stray `--cycles 1`
  during manual testing, while still leaving a documented escape hatch for
  development.
- **SSE streaming is required against the live kimi-k3 API, not optional.**
  Discovered by live debugging: a non-streaming completion for a moderate
  (~2KB) generation never returned (confirmed not an auth, rate-limit, or
  aiohttp-transport-specific issue -- ruled out each individually against
  the real API); the identical request with streaming enabled returned its
  first byte in ~2s and completed a ~15KB response in ~5 minutes. kimi-k3's
  always-on thinking mode means a non-streaming response sends zero bytes
  until the entire completion is ready, which is exactly the shape of
  request an idle-connection timeout somewhere in the network path (proxy,
  load balancer, etc.) will silently kill. The orchestrator therefore always
  passes `RunConfig(streaming_mode=StreamingMode.SSE)` to `Runner.run_async`
  (`orchestrator.py`); `DEFAULT_AGENT_TIMEOUT_SECONDS` was raised to 2400s
  (configurable via `AGENTIC_BUILDER_AGENT_TIMEOUT_SECONDS`) to accommodate
  the resulting multi-minute real completions on large requirement sets.
- **Greenfield deliverable**: this repository ships the reusable
  orchestration project itself, not a pre-generated example web app.
  `requirements/` starts with only a placeholder README (real
  `specification.md`/`layout.md`/`front-back-end-stack.md` are supplied by
  a user later; the input directory itself is configurable via
  `--input-dir`). `tests/fixtures/` holds clearly-labeled example and
  adversarial requirement sets used exclusively by the automated test
  suite, never referenced by default CLI invocation. `frontend/`,
  `backend/`, `testcase/`, and `scripts/` start with placeholder READMEs
  and are populated only by actual runs (fake-model or real) against real
  or fixture input.

## Unresolved / out of scope

- No live-credential validation run has been performed against the real
  Moonshot API from this environment (no API key available here). The
  fake-model path is fully exercised and tested; a real run requires a
  user-supplied `MODEL_API_KEY`.
- Exact litellm/ADK exception classes surfaced for a genuinely invalid
  model id or auth failure are caught broadly (by litellm's documented
  `APIError`/`AuthenticationError`/`NotFoundError` family) and normalized
  into `ModelResolutionError`; if a future litellm release renames these,
  the catch clause in `models/provider.py` will need updating.
