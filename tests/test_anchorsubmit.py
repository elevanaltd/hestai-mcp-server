"""
Test suite for anchor_submit Context Steward tool.

Tests anchor validation, drift detection, and enforcement rule application.
"""

import json
import shutil
from pathlib import Path

import pytest

from tools.anchorsubmit import AnchorSubmitRequest, AnchorSubmitTool


@pytest.fixture
def temp_hestai_dir(tmp_path):
    """Create a temporary .hestai directory structure"""
    hestai_dir = tmp_path / ".hestai"
    sessions_dir = hestai_dir / "sessions"
    active_dir = sessions_dir / "active"

    # Create directory structure
    active_dir.mkdir(parents=True)

    # Create active session
    session_id = "test-1234"
    session_dir = active_dir / session_id
    session_dir.mkdir()

    session_data = {
        "session_id": session_id,
        "role": "implementation-lead",
        "focus": "b2-implementation",
        "working_dir": str(tmp_path),
        "started_at": "2025-12-08T10:00:00",
    }
    (session_dir / "session.json").write_text(json.dumps(session_data))

    yield hestai_dir, session_id

    # Cleanup
    if hestai_dir.exists():
        shutil.rmtree(hestai_dir)


@pytest.fixture
def valid_anchor():
    """Create a valid anchor structure"""
    return {
        "SHANK": {
            "role": "implementation-lead",
            "cognition": "LOGOS",
            "archetypes": ["HEPHAESTUS", "ATLAS", "HERMES"],
            "key_constraints": ["TDD_discipline", "code_review_mandatory", "quality_gates"],
        },
        "ARM": {
            "phase_context": "B2: Implementation phase",
            "current_focus": "Context Steward tool implementation",
            "blockers": [],
        },
        "FLUKE": {
            "skills_loaded": ["build-execution", "test-methodology"],
            "patterns_active": ["TDD", "atomic_commits"],
        },
    }


@pytest.fixture
def anchorsubmit_tool():
    """Create an AnchorSubmitTool instance"""
    return AnchorSubmitTool()


class TestAnchorSubmitTool:
    """Test suite for AnchorSubmitTool"""

    def test_tool_metadata(self, anchorsubmit_tool):
        """Test tool has correct name and metadata"""
        assert anchorsubmit_tool.get_name() == "anchorsubmit"
        assert "anchor" in anchorsubmit_tool.get_description().lower()
        assert anchorsubmit_tool.requires_model() is False

    def test_request_validation_success(self, valid_anchor):
        """Test request validation with valid input"""
        request = AnchorSubmitRequest(
            session_id="test-1234", working_dir="/Volumes/HestAI-Tools/test-project", anchor=valid_anchor
        )
        assert request.session_id == "test-1234"
        assert request.working_dir == "/Volumes/HestAI-Tools/test-project"
        assert request.anchor == valid_anchor

    def test_request_validation_missing_required_fields(self):
        """Test request validation fails with missing required fields"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AnchorSubmitRequest(session_id="test-1234")  # missing working_dir and anchor

    @pytest.mark.asyncio
    async def test_anchorsubmit_validates_complete_structure(self, anchorsubmit_tool, temp_hestai_dir, valid_anchor):
        """Test anchor_submit validates complete SHANK+ARM+FLUKE structure"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        arguments = {
            "session_id": session_id,
            "working_dir": str(working_dir),
            "anchor": valid_anchor,
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await anchorsubmit_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert content["validated"] is True
        assert "anchor_path" in content
        assert "enforcement" in content

    @pytest.mark.asyncio
    async def test_anchorsubmit_rejects_missing_shank(self, anchorsubmit_tool, temp_hestai_dir, valid_anchor):
        """Test anchor_submit rejects anchor with missing SHANK"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        # Remove SHANK
        invalid_anchor = valid_anchor.copy()
        del invalid_anchor["SHANK"]

        arguments = {
            "session_id": session_id,
            "working_dir": str(working_dir),
            "anchor": invalid_anchor,
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await anchorsubmit_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        # Should be error status
        assert output["status"] == "error"
        assert "SHANK" in output["content"]

    @pytest.mark.asyncio
    async def test_anchorsubmit_rejects_missing_arm(self, anchorsubmit_tool, temp_hestai_dir, valid_anchor):
        """Test anchor_submit rejects anchor with missing ARM"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        # Remove ARM
        invalid_anchor = valid_anchor.copy()
        del invalid_anchor["ARM"]

        arguments = {
            "session_id": session_id,
            "working_dir": str(working_dir),
            "anchor": invalid_anchor,
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await anchorsubmit_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        # Should be error status
        assert output["status"] == "error"
        assert "ARM" in output["content"]

    @pytest.mark.asyncio
    async def test_anchorsubmit_rejects_missing_fluke(self, anchorsubmit_tool, temp_hestai_dir, valid_anchor):
        """Test anchor_submit rejects anchor with missing FLUKE"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        # Remove FLUKE
        invalid_anchor = valid_anchor.copy()
        del invalid_anchor["FLUKE"]

        arguments = {
            "session_id": session_id,
            "working_dir": str(working_dir),
            "anchor": invalid_anchor,
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await anchorsubmit_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        # Should be error status
        assert output["status"] == "error"
        assert "FLUKE" in output["content"]

    @pytest.mark.asyncio
    async def test_anchorsubmit_stores_anchor_file(self, anchorsubmit_tool, temp_hestai_dir, valid_anchor):
        """Test anchor_submit stores anchor to session directory"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        arguments = {
            "session_id": session_id,
            "working_dir": str(working_dir),
            "anchor": valid_anchor,
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await anchorsubmit_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        anchor_path = Path(content["anchor_path"])

        # Verify anchor file was created
        assert anchor_path.exists()
        assert anchor_path.parent == hestai_dir / "sessions" / "active" / session_id

        # Verify anchor content
        anchor_data = json.loads(anchor_path.read_text())
        assert anchor_data["SHANK"] == valid_anchor["SHANK"]
        assert anchor_data["ARM"] == valid_anchor["ARM"]
        assert anchor_data["FLUKE"] == valid_anchor["FLUKE"]

    @pytest.mark.asyncio
    async def test_anchorsubmit_returns_ho_blocked_paths(self, anchorsubmit_tool, temp_hestai_dir, valid_anchor):
        """Test anchor_submit returns blocked paths for holistic-orchestrator"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        # Update session to holistic-orchestrator role
        session_dir = hestai_dir / "sessions" / "active" / session_id
        session_file = session_dir / "session.json"
        session_data = json.loads(session_file.read_text())
        session_data["role"] = "holistic-orchestrator"
        session_file.write_text(json.dumps(session_data))

        # Update anchor role
        ho_anchor = valid_anchor.copy()
        ho_anchor["SHANK"]["role"] = "holistic-orchestrator"

        arguments = {
            "session_id": session_id,
            "working_dir": str(working_dir),
            "anchor": ho_anchor,
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await anchorsubmit_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert content["validated"] is True

        # Should have blocked paths for holistic-orchestrator
        enforcement = content["enforcement"]
        assert "blocked_paths" in enforcement
        assert len(enforcement["blocked_paths"]) > 0
        assert "src/**" in enforcement["blocked_paths"]
        assert "delegation_required" in enforcement
        assert "implementation-lead" in enforcement["delegation_required"]

    @pytest.mark.asyncio
    async def test_anchorsubmit_returns_empty_blocked_for_il(self, anchorsubmit_tool, temp_hestai_dir, valid_anchor):
        """Test anchor_submit returns empty blocked paths for implementation-lead"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        arguments = {
            "session_id": session_id,
            "working_dir": str(working_dir),
            "anchor": valid_anchor,  # role is implementation-lead
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await anchorsubmit_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert content["validated"] is True

        # Should have empty blocked paths for implementation-lead
        enforcement = content["enforcement"]
        assert "blocked_paths" in enforcement
        assert len(enforcement["blocked_paths"]) == 0
        assert "delegation_required" in enforcement
        assert len(enforcement["delegation_required"]) == 0

    @pytest.mark.asyncio
    async def test_anchorsubmit_handles_unknown_role(self, anchorsubmit_tool, temp_hestai_dir, valid_anchor):
        """Test anchor_submit handles unknown role with default enforcement"""
        hestai_dir, session_id = temp_hestai_dir
        working_dir = hestai_dir.parent

        # Update anchor to unknown role
        unknown_anchor = valid_anchor.copy()
        unknown_anchor["SHANK"]["role"] = "unknown-role"

        arguments = {
            "session_id": session_id,
            "working_dir": str(working_dir),
            "anchor": unknown_anchor,
            "_session_context": type("obj", (object,), {"project_root": working_dir})(),
        }

        result = await anchorsubmit_tool.execute(arguments)

        # Parse result
        result_text = result[0].text
        output = json.loads(result_text)

        assert output["status"] == "success"

        # Content is JSON-encoded
        content = json.loads(output["content"])
        assert content["validated"] is True

        # Should use default enforcement (empty)
        enforcement = content["enforcement"]
        assert "blocked_paths" in enforcement
        assert "delegation_required" in enforcement

    def test_anchorsubmit_rejects_path_traversal_session_id(self):
        """Test session_id with ../ is rejected to prevent path traversal"""
        from pydantic import ValidationError

        valid_anchor = {
            "SHANK": {"role": "test", "cognition": "LOGOS", "archetypes": [], "key_constraints": []},
            "ARM": {"phase_context": "B2", "current_focus": "test", "blockers": []},
            "FLUKE": {"skills_loaded": [], "patterns_active": []},
        }

        # Path traversal attempts should be rejected
        with pytest.raises(ValidationError, match="Invalid session_id"):
            AnchorSubmitRequest(session_id="../../../etc/passwd", working_dir="/tmp/test", anchor=valid_anchor)

    def test_anchorsubmit_rejects_session_id_with_forward_slash(self):
        """Test session_id with forward slash is rejected"""
        from pydantic import ValidationError

        valid_anchor = {
            "SHANK": {"role": "test", "cognition": "LOGOS", "archetypes": [], "key_constraints": []},
            "ARM": {"phase_context": "B2", "current_focus": "test", "blockers": []},
            "FLUKE": {"skills_loaded": [], "patterns_active": []},
        }

        with pytest.raises(ValidationError, match="Invalid session_id"):
            AnchorSubmitRequest(session_id="test/session", working_dir="/tmp/test", anchor=valid_anchor)

    def test_anchorsubmit_rejects_session_id_with_backslash(self):
        """Test session_id with backslash is rejected"""
        from pydantic import ValidationError

        valid_anchor = {
            "SHANK": {"role": "test", "cognition": "LOGOS", "archetypes": [], "key_constraints": []},
            "ARM": {"phase_context": "B2", "current_focus": "test", "blockers": []},
            "FLUKE": {"skills_loaded": [], "patterns_active": []},
        }

        with pytest.raises(ValidationError, match="Invalid session_id"):
            AnchorSubmitRequest(session_id="test\\session", working_dir="/tmp/test", anchor=valid_anchor)

    def test_anchorsubmit_rejects_empty_session_id(self):
        """Test empty session_id is rejected"""
        from pydantic import ValidationError

        valid_anchor = {
            "SHANK": {"role": "test", "cognition": "LOGOS", "archetypes": [], "key_constraints": []},
            "ARM": {"phase_context": "B2", "current_focus": "test", "blockers": []},
            "FLUKE": {"skills_loaded": [], "patterns_active": []},
        }

        with pytest.raises(ValidationError, match="Session ID cannot be empty"):
            AnchorSubmitRequest(session_id="", working_dir="/tmp/test", anchor=valid_anchor)

    def test_anchorsubmit_rejects_whitespace_session_id(self):
        """Test whitespace-only session_id is rejected"""
        from pydantic import ValidationError

        valid_anchor = {
            "SHANK": {"role": "test", "cognition": "LOGOS", "archetypes": [], "key_constraints": []},
            "ARM": {"phase_context": "B2", "current_focus": "test", "blockers": []},
            "FLUKE": {"skills_loaded": [], "patterns_active": []},
        }

        with pytest.raises(ValidationError, match="Session ID cannot be empty"):
            AnchorSubmitRequest(session_id="   ", working_dir="/tmp/test", anchor=valid_anchor)
