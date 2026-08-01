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
