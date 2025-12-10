## PR Title Format

**Please ensure your PR title follows one of these formats:**

### Version Bumping Prefixes (trigger Docker build + version bump):
- `feat: <description>` - New features (triggers MINOR version bump)
- `fix: <description>` - Bug fixes (triggers PATCH version bump)
- `breaking: <description>` or `BREAKING CHANGE: <description>` - Breaking changes (triggers MAJOR version bump)
- `perf: <description>` - Performance improvements (triggers PATCH version bump)
- `refactor: <description>` - Code refactoring (triggers PATCH version bump)

### Non-Version Prefixes (no version bump):
- `docs: <description>` - Documentation only
- `chore: <description>` - Maintenance tasks
- `test: <description>` - Test additions/changes
- `ci: <description>` - CI/CD changes
- `style: <description>` - Code style changes

### Docker Build Options:
- `docker: <description>` - Force Docker build without version bump
- `docs+docker: <description>` - Documentation + Docker build
- `chore+docker: <description>` - Maintenance + Docker build
- `test+docker: <description>` - Tests + Docker build
- `ci+docker: <description>` - CI changes + Docker build
- `style+docker: <description>` - Style changes + Docker build

## Description

Please provide a clear and concise description of what this PR does.

## Changes Made

- [ ] List the specific changes made
- [ ] Include any breaking changes
- [ ] Note any dependencies added/removed

## Testing

**Please review our [Testing Guide](../docs/testing.md) before submitting.**

### Run all linting and tests (required):
```bash
# Activate virtual environment first
source venv/bin/activate

# Run comprehensive code quality checks (recommended)
./code_quality_checks.sh

# If you made tool changes, also run simulator tests
python communication_simulator_test.py
```

- [ ] All linting passes (ruff, black, isort)
- [ ] All unit tests pass
- [ ] **For new features**: Unit tests added in `tests/`
- [ ] **For tool changes**: Simulator tests added in `simulator_tests/`
- [ ] **For bug fixes**: Tests added to prevent regression
- [ ] Simulator tests pass (if applicable)
- [ ] Manual testing completed with realistic scenarios

## Related Issues

Fixes #(issue number)

## Checklist

- [ ] PR title follows the format guidelines above
- [ ] **Activated venv and ran code quality checks: `source venv/bin/activate && ./code_quality_checks.sh`**
- [ ] Self-review completed
- [ ] **Tests added for ALL changes** (see Testing section above)
- [ ] Documentation updated as needed
- [ ] All unit tests passing
- [ ] Relevant simulator tests passing (if tool changes)
- [ ] Ready for review

## Additional Notes

Any additional information that reviewers should know.

---

## Snapshot Contract Validation (If Applicable)

<!-- ⚠️ CRITICAL: Only complete this section if PR adds/modifies files in tests/snapshots/ -->
<!-- This section enforces test methodology guardian protocol for contract correctness -->

### Does this PR modify snapshot files?

- [ ] Yes - Complete validation checklist below
- [ ] No - Skip this section

### Snapshot Validation Checklist

**For each modified snapshot file, reviewer MUST verify:**

#### Cross-Reference Validation (Critical - Automated by Meta-Test)

The automated meta-test (`tests/test_schema_source_parity.py`) will verify:
- [ ] Schema matches source Pydantic model (tool implementation)
- [ ] All parameters from model present in snapshot
- [ ] Required fields match actual tool enforcement
- [ ] Type constraints accurate (enums, min/max, patterns)

**If meta-test fails, the snapshot contract has drifted from its source of truth.**

#### Human Review Requirements (Not Automated)

Reviewer must manually verify:
- [ ] Field descriptions are accurate and helpful
- [ ] Enum values match actual application constraints
- [ ] Default values are appropriate for the use case
- [ ] Optional parameters properly marked and documented

#### Completeness Check

- [ ] All tool parameters documented in schema
- [ ] No placeholder or dummy values present
- [ ] JSON syntax valid (no trailing commas, proper escaping)
- [ ] Formatting consistent with other snapshots

#### Regression Prevention

- [ ] If schema existed before, breaking changes documented in PR description
- [ ] Intentional changes justified with clear rationale
- [ ] Unexpected differences investigated and explained

### Guardian Protocol Compliance

**Contract-Driven-Correction:** Snapshots define test contracts. Contracts must be correct before enforcement.

**Truth Over Convenience:** Do not approve snapshots that validate current behavior if that behavior is incorrect.

**Process Integrity:** New snapshots require two-PR process:
1. First PR: Establish baseline (snapshots only)
2. Second PR: Enforce contract (code + tests validate against baseline)
