"""
Typed models for secure session context passing between MCP server and tools.

This module provides Pydantic models that enforce type safety and data contracts
for session context, replacing brittle dictionary-based context passing.

// Critical-Engineer: consulted for Project-Aware Context Isolation and security hardening
// Context7: consulted for pydantic
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class SessionContextModel(BaseModel):
    """
    Typed session context model for secure tool execution.
    
    This replaces dictionary-based context passing with a typed, validated model
    that enforces the data contract between the MCP server and tools.
    """
    
    session_id: str = Field(..., description="Unique session identifier")
    project_root: Path = Field(..., description="Validated project root path")
    
    model_config = ConfigDict(
        # Allow Path objects which aren't JSON serializable by default
        arbitrary_types_allowed=True,
        # Validate on assignment to catch issues early
        validate_assignment=True
    )
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Session ID cannot be empty")
        return v.strip()
    
    @field_validator('project_root')
    @classmethod
    def validate_project_root(cls, v):
        if not isinstance(v, Path):
            v = Path(v)
        
        # Ensure it's absolute for security
        if not v.is_absolute():
            raise ValueError(f"Project root must be absolute path: {v}")
        
        # SECURITY: Prevent path traversal attacks
        if ".." in v.parts:
            raise ValueError(f"Path traversal detected in project root: {v}")
        
        return v
    
    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "session_id": self.session_id,
            "project_root": str(self.project_root),
        }
    
    @classmethod
    def from_session_context(cls, session_context: "SessionContext") -> "SessionContextModel":
        """Create from SessionContext object."""
        return cls(
            session_id=session_context.session_id,
            project_root=session_context.project_root
        )


class ToolExecutionContext(BaseModel):
    """
    Complete execution context for tool runs including session and metadata.
    
    This model encapsulates all context needed for secure tool execution,
    including session isolation, model context, and security boundaries.
    """
    
    session: SessionContextModel = Field(..., description="Session context for project isolation")
    remaining_tokens: Optional[int] = Field(None, description="Remaining token budget for this execution")
    model_name: Optional[str] = Field(None, description="Model being used for this execution")
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True
    )
    
    def get_project_root(self) -> Path:
        """Get the validated project root path."""
        return self.session.project_root
    
    def get_session_id(self) -> str:
        """Get the session identifier."""
        return self.session.session_id
