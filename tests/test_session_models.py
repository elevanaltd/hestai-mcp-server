"""
Tests for typed session context models.

Tests the Pydantic models that replace dictionary-based context passing
for secure session management and type safety.

// Context7: consulted for pydantic
// Context7: consulted for tools
"""

import pytest
from pathlib import Path
from pydantic import ValidationError

# Import the models we're testing - will fail initially (RED phase)
from tools.shared.session_models import SessionContextModel, ToolExecutionContext


class TestSessionContextModel:
    """Test the SessionContextModel Pydantic model."""
    
    def test_valid_session_context(self):
        """Test creating a valid SessionContextModel."""
        # RED: This test should fail initially
        session = SessionContextModel(
            session_id="test-session-123",
            project_root=Path("/tmp/test-project")
        )
        
        assert session.session_id == "test-session-123"
        assert session.project_root == Path("/tmp/test-project")
        assert session.project_root.is_absolute()
    
    def test_session_id_validation(self):
        """Test session ID validation."""
        # RED: Should fail - empty session ID should be rejected
        with pytest.raises(ValidationError) as exc_info:
            SessionContextModel(
                session_id="",
                project_root=Path("/tmp/test")
            )
        
        assert "Session ID cannot be empty" in str(exc_info.value)
        
        # Test whitespace-only session ID
        with pytest.raises(ValidationError):
            SessionContextModel(
                session_id="   ",
                project_root=Path("/tmp/test")
            )
    
    def test_project_root_validation(self):
        """Test project root path validation."""
        # RED: Should fail - relative paths should be rejected
        with pytest.raises(ValidationError) as exc_info:
            SessionContextModel(
                session_id="test-session",
                project_root=Path("relative/path")
            )
        
        assert "Project root must be absolute path" in str(exc_info.value)
    
    def test_to_dict_conversion(self):
        """Test conversion to dictionary for backward compatibility."""
        # RED: This method should exist but doesn't yet
        session = SessionContextModel(
            session_id="test-session",
            project_root=Path("/tmp/test-project")
        )
        
        result = session.to_dict()
        expected = {
            "session_id": "test-session",
            "project_root": "/tmp/test-project"
        }
        
        assert result == expected
    
    def test_from_session_context_creation(self):
        """Test creating SessionContextModel from SessionContext object."""
        # RED: This class method should exist but doesn't yet
        # Mock SessionContext object
        class MockSessionContext:
            def __init__(self):
                self.session_id = "mock-session"
                self.project_root = Path("/tmp/mock-project")
        
        mock_context = MockSessionContext()
        session = SessionContextModel.from_session_context(mock_context)
        
        assert session.session_id == "mock-session"
        assert session.project_root == Path("/tmp/mock-project")


class TestToolExecutionContext:
    """Test the ToolExecutionContext model."""
    
    def test_valid_execution_context(self):
        """Test creating a valid ToolExecutionContext."""
        # RED: This should fail initially
        session = SessionContextModel(
            session_id="exec-session",
            project_root=Path("/tmp/exec-project")
        )
        
        context = ToolExecutionContext(
            session=session,
            remaining_tokens=5000,
            model_name="gpt-4"
        )
        
        assert context.session.session_id == "exec-session"
        assert context.remaining_tokens == 5000
        assert context.model_name == "gpt-4"
    
    def test_get_project_root(self):
        """Test the get_project_root convenience method."""
        # RED: This method should exist but doesn't yet
        session = SessionContextModel(
            session_id="test",
            project_root=Path("/tmp/test")
        )
        
        context = ToolExecutionContext(session=session)
        
        assert context.get_project_root() == Path("/tmp/test")
    
    def test_get_session_id(self):
        """Test the get_session_id convenience method."""
        # RED: This method should exist but doesn't yet
        session = SessionContextModel(
            session_id="test-id",
            project_root=Path("/tmp/test")
        )
        
        context = ToolExecutionContext(session=session)
        
        assert context.get_session_id() == "test-id"
    
    def test_optional_fields(self):
        """Test that remaining_tokens and model_name are optional."""
        # RED: Should work but model doesn't exist yet
        session = SessionContextModel(
            session_id="minimal",
            project_root=Path("/tmp/minimal")
        )
        
        context = ToolExecutionContext(session=session)
        
        assert context.remaining_tokens is None
        assert context.model_name is None


class TestSecurityValidation:
    """Test security-focused validation behavior."""
    
    def test_path_traversal_prevention(self):
        """Test that path traversal attempts are blocked."""
        # RED: Should prevent path traversal
        dangerous_paths = [
            "../../../etc/passwd",
            "../../sensitive",
            "/tmp/../../../etc"
        ]
        
        for dangerous_path in dangerous_paths:
            with pytest.raises(ValidationError):
                SessionContextModel(
                    session_id="dangerous",
                    project_root=Path(dangerous_path)
                )
    
    def test_fail_fast_validation(self):
        """Test that validation fails fast on invalid data."""
        # RED: Should fail immediately, not silently
        with pytest.raises(ValidationError):
            SessionContextModel(
                session_id=None,  # Invalid
                project_root=Path("/tmp/test")
            )
        
        with pytest.raises(ValidationError):
            SessionContextModel(
                session_id="valid",
                project_root=None  # Invalid
            )