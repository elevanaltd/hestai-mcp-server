# Phase 0.75 Mandatory Task: model_restrictions.py Alias Resolution Fix

**Priority:** 🔴 **CRITICAL** - Must complete before Phase 1
**Discovered:** STEP 4 Utils Validation (2025-10-07)
**Analyst:** Technical-Architect (TRACED protocol)
**Validator:** Critical-Engineer

---

## Problem

**Latent Bug:** Users configuring allowed models with **aliases** will experience valid requests incorrectly rejected.

**Example Failure Scenario:**
```bash
# User configuration
export ANTHROPIC_ALLOWED_MODELS="opus-latest,sonnet-latest"

# User request
model="claude-3-opus-20240229"  # Canonical name for opus-latest

# Current behavior
REJECTED - Can't match "claude-3-opus-20240229" to "opus-latest"

# Expected behavior
ALLOWED - Should resolve alias to canonical name
```

---

## Root Cause

**HestAI Implementation:**
```python
# utils/model_restrictions.py (current)
def is_allowed(self, provider_type: ProviderType, model_name: str) -> bool:
    # Only checks direct string match
    return model_name.lower() in allowed_set
```

**Zen Fix:**
```python
# Adds alias resolution cache and provider lookup
self._alias_resolution_cache: dict[ProviderType, dict[str, str]] = defaultdict(dict)

# Resolves aliases before checking
for allowed_entry in allowed_set:
    resolved = provider._resolve_model_name(allowed_entry)  # opus-latest → claude-3-opus-20240229
    if resolved.lower() in names_to_check:
        return True
```

---

## Why Deferred to Phase 0.75

**Architectural Coupling:**
- Zen refactored `ProviderType` from `providers/base.py` → `providers/shared/provider_type.py`
- Fix requires this structural change
- Can't port fix independently without full provider refactor

**Phase 0.75 Context:**
- Gemini SDK migration (`google.generativeai` → `google-genai`)
- ALL providers will be touched anyway
- Natural coupling point for provider architecture alignment

**Constitutional Compliance:**
- Line 84 (MINIMAL_INTERVENTION): Don't refactor providers just for this bug
- Line 169 (MANDATORY_PARALLELIZATION): Couple related provider changes

---

## Required Changes (Phase 0.75)

### 1. Port Provider Shared Structure
```bash
# Create providers/shared/ directory
mkdir -p providers/shared

# Port from Zen:
providers/shared/__init__.py
providers/shared/provider_type.py      # ProviderType enum
providers/shared/model_capabilities.py
providers/shared/model_response.py
providers/shared/temperature.py
```

### 2. Update model_restrictions.py
```python
# Change imports
from collections import defaultdict
from providers.shared import ProviderType  # Was: providers.base
from utils.env import get_env             # Was: os.getenv

# Add cache
self._alias_resolution_cache: dict[ProviderType, dict[str, str]] = defaultdict(dict)

# Add alias resolution logic (see Zen implementation lines 91-122)
```

### 3. Update All Provider Imports
```bash
# Find all files importing from providers.base
grep -r "from providers.base import" .

# Update to providers.shared where appropriate
```

### 4. Add Guardrail Test
```python
# tests/utils/test_model_restrictions.py
def test_alias_resolution():
    """Verify alias resolution works (opus-latest → claude-3-opus-20240229)"""
    os.environ['ANTHROPIC_ALLOWED_MODELS'] = 'opus-latest,sonnet-latest'
    service = ModelRestrictionService()

    # Should allow canonical names when alias is configured
    assert service.is_allowed(ProviderType.OPENAI, 'claude-3-opus-20240229')
    assert service.is_allowed(ProviderType.OPENAI, 'claude-3-5-sonnet-20241022')
```

---

## Risk Assessment

**If Not Fixed:**
- **Production Impact:** Valid model requests rejected for users using alias configuration
- **User Experience:** Confusing error messages ("model not allowed")
- **Workaround:** Users must configure canonical names (defeats alias purpose)
- **Probability:** MEDIUM (depends on user configuration patterns)

**If Fixed in Phase 0.75:**
- **Coupling Benefit:** Natural fit with provider refactor
- **Test Coverage:** Can validate with Gemini SDK changes
- **Risk:** LOW (changes already bundled with provider migration)

---

## Verification Checklist

- [ ] `providers/shared/` structure ported
- [ ] `model_restrictions.py` updated with alias cache
- [ ] All provider imports updated
- [ ] Guardrail test added and passing
- [ ] Existing tests still passing
- [ ] Manual test with alias configuration
- [ ] Documentation updated

---

## Evidence Files

- `decision-records/2025-10-07_step4-utils-validation/evidence-diffs/model_restrictions.diff` (126 lines)
- This mandate document

---

**Status:** 📋 **TRACKED** - Must complete in Phase 0.75
**Next Review:** During Phase 0.75 provider migration planning
