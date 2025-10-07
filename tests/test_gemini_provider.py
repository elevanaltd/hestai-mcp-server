"""Test Gemini provider with new google-genai SDK (Phase 0.75)

This test validates Phase 0.75 provider architecture refactor.
It MUST fail until Gemini provider migrates from deprecated SDK.

Constitutional requirement: RED state before implementation (Line 52)
"""

import inspect

import pytest


def test_gemini_provider_imports():
    """Verify Gemini provider uses new SDK (google-genai not google.generativeai)

    Phase 0.75 requirement: Migrate from deprecated google.generativeai to google-genai

    Expected: FAIL until providers/gemini.py migrates to new SDK
    """
    import providers.gemini

    # Get source code of module (not just class)
    source = inspect.getsource(providers.gemini)

    # Verify NEW SDK import
    assert 'from google import genai' in source, \
        "Should use new SDK: from google import genai"

    # Verify OLD SDK not present
    assert 'import google.generativeai' not in source, \
        "Should NOT use deprecated SDK: google.generativeai"


def test_gemini_provider_no_deprecated_configure():
    """Verify Gemini provider doesn't use deprecated genai.configure() pattern

    Expected: FAIL until migration complete
    """
    from providers.gemini import GeminiModelProvider

    source = inspect.getsource(GeminiModelProvider)

    # Verify no deprecated configure() call
    assert 'genai.configure(' not in source, \
        "Should NOT use deprecated genai.configure() - use Client() instead"


def test_gemini_provider_uses_client_pattern():
    """Verify Gemini provider uses new Client() pattern

    Expected: FAIL until migration complete
    """
    from providers.gemini import GeminiModelProvider

    source = inspect.getsource(GeminiModelProvider)

    # Verify Client() pattern usage
    assert 'genai.Client(' in source or 'Client(' in source, \
        "Should use new Client() pattern for SDK initialization"
