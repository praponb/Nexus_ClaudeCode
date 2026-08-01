<!-- Example/test fixture only. Intentionally omits layout.md and
     front-back-end-stack.md to exercise required-file validation. -->

# Specification: Incomplete Example

This fixture deliberately has only one of the three required requirement
files, to test that `load_and_validate_inputs` raises `InputValidationError`
listing the missing files.
