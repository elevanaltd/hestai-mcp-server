"""
Meta-test: Validates snapshot contracts match their Pydantic source models.

Per testguard guidance: This automated test ensures contracts cannot drift
from their source of truth. It is the implementation of CONSTRAINT CATALYSIS.

Guardian Protocol: Contract-driven-correction with automated verification.
"""

import json
from pathlib import Path

import pytest

from tools.consensus import ConsensusRequest
from tools.critical_engineer import CriticalEngineerRequest
from tools.debug import DebugInvestigationRequest

# Central mapping of contracts to their source-of-truth models.
# To add a new schema, simply add a tuple to this list.
SCHEMA_MODEL_MAP = [
    ("consensus_schema.json", ConsensusRequest),
    ("debug_schema.json", DebugInvestigationRequest),
    ("critical_engineer_schema.json", CriticalEngineerRequest),
]


@pytest.mark.parametrize("snapshot_filename,pydantic_model", SCHEMA_MODEL_MAP)
def test_snapshot_contract_matches_pydantic_source(snapshot_filename, pydantic_model):
    """
    Asserts that a snapshot's inputSchema matches the schema generated
    from its corresponding Pydantic model.

    This test enforces the guardian protocol: snapshots are contracts,
    and contracts must match their source of truth (Pydantic models).

    If this test fails, the snapshot has drifted from the model definition.
    """
    # 1. Generate schema from Pydantic model (Source of Truth)
    model_schema = pydantic_model.model_json_schema()

    # 2. Load snapshot file (The Contract)
    # Use absolute path relative to this test file for cross-platform compatibility
    snapshot_path = Path(__file__).parent / "snapshots" / snapshot_filename

    # Ensure snapshot exists with helpful error message
    if not snapshot_path.exists():
        pytest.fail(
            f"Snapshot file not found: {snapshot_path}\n"
            f"Working directory: {Path.cwd()}\n"
            f"Test file location: {__file__}"
        )

    with open(snapshot_path) as f:
        snapshot_schema = json.load(f)

    # 3. Assert: The contract must match the source of truth.
    assert snapshot_schema == model_schema, (
        f"CONTRACT DRIFT DETECTED! The snapshot '{snapshot_filename}' is out of sync "
        f"with its source Pydantic model '{pydantic_model.__name__}'.\n\n"
        f"Guardian Protocol Violation: Snapshots define test contracts. "
        f"Contracts must remain synchronized with their implementation models.\n\n"
        f"Resolution: Update the snapshot to match the current model schema, "
        f"or update the model if the snapshot represents the correct contract."
    )
