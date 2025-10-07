"""Test providers/shared structure

This test validates Phase 0.75 provider architecture refactor.
It MUST fail until providers/shared/ is created with ProviderType enum.

Constitutional requirement: RED state before implementation (Line 52)
"""


def test_providertype_import():
    """Verify ProviderType can be imported from providers.shared

    This test enforces:
    - providers/shared/__init__.py must exist
    - ProviderType enum must be defined
    - Standard provider types must be available

    Expected: FAIL until providers/shared/ created
    """
    from providers.shared import ProviderType

    # Verify enum values exist
    assert hasattr(ProviderType, "GOOGLE"), "ProviderType.GOOGLE must exist"
    assert hasattr(ProviderType, "OPENAI"), "ProviderType.OPENAI must exist"
    assert hasattr(ProviderType, "OPENROUTER"), "ProviderType.OPENROUTER must exist"
    assert hasattr(ProviderType, "CUSTOM"), "ProviderType.CUSTOM must exist"


def test_providertype_values():
    """Verify ProviderType enum has correct string values

    Expected: FAIL until providers/shared/ created
    """
    from providers.shared import ProviderType

    # Verify enum string values match provider names
    assert ProviderType.GOOGLE.value == "google"
    assert ProviderType.OPENAI.value == "openai"
    assert ProviderType.OPENROUTER.value == "openrouter"
    assert ProviderType.CUSTOM.value == "custom"
