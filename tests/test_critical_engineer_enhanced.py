"""
Tests for enhanced CriticalEngineer with file context capabilities

This module tests the enhanced critical-engineer tool that can access
file context for more informed architectural validation.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.critical_engineer import CriticalEngineerRequest, CriticalEngineerTool


class TestCriticalEngineerEnhanced:
    """Test suite for enhanced critical-engineer with file context"""

    @pytest.fixture
    def tool(self):
        """Create a CriticalEngineerTool instance"""
        return CriticalEngineerTool()

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider"""
        provider = AsyncMock()
        provider.chat_completion = AsyncMock(
            return_value="VIABILITY_ASSESSMENT: VIABLE\n\nValidation complete."
        )
        return provider

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Create a simple project structure
            (root / "src").mkdir()
            (root / "src" / "api.py").write_text("""
class APIHandler:
    def process_request(self, data):
        # No validation!
        return data['value'] * 2
""")
            (root / "src" / "database.py").write_text("""
import sqlite3

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
    
    def query(self, sql):
        # Direct SQL execution - SQL injection risk!
        return self.conn.execute(sql)
""")
            (root / "tests").mkdir()
            (root / "tests" / "test_api.py").write_text("""
def test_process_request():
    # Minimal test coverage
    assert True
""")
            (root / "requirements.txt").write_text("flask==2.0.0\nsqlite3")
            
            yield root

    async def test_request_with_files(self, tool, temp_project):
        """Test that request can include file paths"""
        request = CriticalEngineerRequest(
            prompt="Validate the API handler architecture",
            files=[
                str(temp_project / "src" / "api.py"),
                str(temp_project / "src" / "database.py")
            ]
        )
        
        assert request.files is not None
        assert len(request.files) == 2
        assert all(isinstance(f, str) for f in request.files)

    async def test_request_with_tree_option(self, tool, temp_project):
        """Test that request can include tree structure option"""
        request = CriticalEngineerRequest(
            prompt="Validate overall system architecture",
            include_tree=True,
            max_depth=3
        )
        
        assert request.include_tree is True
        assert request.max_depth == 3

    async def test_request_backwards_compatible(self, tool):
        """Test that old requests without files still work"""
        request = CriticalEngineerRequest(
            prompt="Validate this architecture decision"
        )
        
        assert request.files is None
        assert request.include_tree is False

    async def test_prepare_prompt_with_files(self, tool, temp_project, mock_llm_provider):
        """Test that prompt preparation includes file context"""
        request = CriticalEngineerRequest(
            prompt="Validate the API security",
            files=[str(temp_project / "src" / "api.py")]
        )
        
        with patch("tools.critical_engineer.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_relevant_files.return_value = {
                "files": [{
                    "path": "src/api.py",
                    "content": "class APIHandler:..."
                }],
                "total_tokens": 50
            }
            
            prompt = await tool.prepare_prompt(request)
            
            # Should include file context in prompt
            assert "FILE CONTEXT:" in prompt or "api.py" in prompt
            mock_instance.get_relevant_files.assert_called_once()

    async def test_prepare_prompt_with_tree(self, tool, temp_project):
        """Test that prompt includes tree structure when requested"""
        request = CriticalEngineerRequest(
            prompt="Validate system architecture",
            include_tree=True,
            max_depth=2
        )
        
        with patch("tools.critical_engineer.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_file_tree.return_value = {
                "structure": "├── src/\n│   ├── api.py\n",
                "total_files": 5,
                "total_dirs": 2
            }
            
            prompt = await tool.prepare_prompt(request)
            
            # Should include tree structure
            assert "DIRECTORY STRUCTURE:" in prompt or "src/" in prompt
            mock_instance.get_file_tree.assert_called_once()

    async def test_architectural_context_auto_discovery(self, tool, temp_project):
        """Test automatic discovery of architectural context"""
        request = CriticalEngineerRequest(
            prompt="Validate database architecture",
            files=["auto"],  # Special value for auto-discovery
            include_tree=True
        )
        
        with patch("tools.critical_engineer.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_architectural_context.return_value = {
                "tree": {"structure": "..."},
                "configs": ["requirements.txt"],
                "entry_points": ["src/api.py"],
                "test_structure": ["tests/"]
            }
            
            prompt = await tool.prepare_prompt(request)
            
            # Should call architectural context
            mock_instance.get_architectural_context.assert_called()

    async def test_validation_with_file_context(self, tool, mock_llm_provider):
        """Test that validation uses file context effectively"""
        request = CriticalEngineerRequest(
            prompt="Validate SQL injection vulnerabilities",
            files=["src/database.py"]
        )
        
        with patch("tools.critical_engineer.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_relevant_files.return_value = {
                "files": [{
                    "path": "src/database.py",
                    "content": "def query(self, sql): return self.conn.execute(sql)"
                }],
                "total_tokens": 30
            }
            
            # Mock the tool's runner
            tool.runner = MagicMock()
            tool.runner.llm_provider_factory.get_provider.return_value = mock_llm_provider
            
            response = await tool.run(request)
            
            # Verify context was used
            mock_instance.get_relevant_files.assert_called()
            
            # The LLM should have been called with context
            mock_llm_provider.chat_completion.assert_called()

    async def test_handle_missing_files_gracefully(self, tool):
        """Test that tool handles missing files gracefully"""
        request = CriticalEngineerRequest(
            prompt="Validate architecture",
            files=["/nonexistent/file.py"]
        )
        
        with patch("tools.critical_engineer.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_relevant_files.return_value = {
                "files": [{
                    "path": "/nonexistent/file.py",
                    "error": "File not found"
                }],
                "total_tokens": 0
            }
            
            prompt = await tool.prepare_prompt(request)
            
            # Should handle gracefully
            assert "error" in prompt.lower() or "not found" in prompt.lower()

    async def test_security_validation_paths(self, tool):
        """Test that dangerous paths are rejected"""
        dangerous_paths = ["/etc/passwd", "../../../etc/passwd"]
        
        for path in dangerous_paths:
            request = CriticalEngineerRequest(
                prompt="Validate",
                files=[path]
            )
            
            with patch("tools.critical_engineer.FileContextProcessor") as mock_processor:
                mock_instance = MagicMock()
                mock_processor.return_value = mock_instance
                mock_instance.get_relevant_files.return_value = {
                    "files": [],
                    "total_tokens": 0,
                    "errors": ["Security: Access denied"]
                }
                
                prompt = await tool.prepare_prompt(request)
                
                # Should not include dangerous content
                assert "/etc/passwd" not in prompt or "denied" in prompt

    async def test_token_budget_management(self, tool):
        """Test that token budget is managed properly"""
        request = CriticalEngineerRequest(
            prompt="Validate",
            files=["file1.py", "file2.py", "file3.py"],
            max_file_tokens=500  # New field for token budget
        )
        
        with patch("tools.critical_engineer.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            
            await tool.prepare_prompt(request)
            
            # Should pass token budget to processor
            mock_instance.get_relevant_files.assert_called()
            call_args = mock_instance.get_relevant_files.call_args
            assert call_args[1]["token_budget"] <= 500

    async def test_auto_find_related_files(self, tool, temp_project):
        """Test automatic discovery of related files"""
        request = CriticalEngineerRequest(
            prompt="Validate API implementation",
            files=[str(temp_project / "src" / "api.py")],
            include_related=True  # New option to find related files
        )
        
        with patch("tools.critical_engineer.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.find_related_files.return_value = [
                str(temp_project / "tests" / "test_api.py")
            ]
            mock_instance.get_relevant_files.return_value = {
                "files": [
                    {"path": "src/api.py", "content": "..."},
                    {"path": "tests/test_api.py", "content": "..."}
                ],
                "total_tokens": 100
            }
            
            await tool.prepare_prompt(request)
            
            # Should find related files
            mock_instance.find_related_files.assert_called()
            # Should include both files
            mock_instance.get_relevant_files.assert_called()
            files_arg = mock_instance.get_relevant_files.call_args[0][0]
            assert len(files_arg) >= 2