# Test fixtures (example-only)

Everything under this directory is example/adversarial data used exclusively
by the automated test suite in `tests/unit/` and `tests/integration/`. None
of it is real project input, and the default CLI invocation never reads
from here -- real requirement files go in the configurable `--input-dir`
(default `requirements/`, which starts empty in this repository).

- `requirements_valid/` -- a small, complete, labeled example app spec used
  by the dry-run and fake-model end-to-end integration tests.
- `requirements_missing_required/` -- intentionally omits required files, to
  test input validation failure.
- `requirements_prompt_injection/` -- contains an embedded adversarial
  instruction, to test that requirement-file content is never treated as
  agent instructions.
