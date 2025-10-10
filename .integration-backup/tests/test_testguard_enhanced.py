"""
Tests for enhanced TestGuard with file context capabilities

This module tests the enhanced testguard tool that can access test files
and implementation files to detect test manipulation anti-patterns.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tools.testguard import RequirementsRequest as TestGuardRequest
from tools.testguard import RequirementsTool as TestGuardTool


class TestTestGuardEnhanced:
    """Test suite for enhanced testguard with file context"""

    @pytest.fixture
    def tool(self):
        """Create a TestGuardTool instance"""
        return TestGuardTool()

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider"""
        provider = AsyncMock()
        provider.chat_completion = AsyncMock(
            return_value="INTERVENTION: No anti-patterns detected. Proceed with testing."
        )
        return provider

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with test manipulation scenarios"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Implementation file
            (root / "src").mkdir()
            (root / "src" / "calculator.py").write_text(
                """
def add(a, b):
    # Bug: should return a + b
    return a - b

def multiply(a, b):
    return a * b
"""
            )

            # Test file with manipulation attempts
            (root / "tests").mkdir()
            (root / "tests" / "test_calculator.py").write_text(
                """
def test_add():
    from src.calculator import add
    # CHANGED: Expected value adjusted to match buggy behavior
    assert add(2, 3) == -1  # Was: assert add(2, 3) == 5

def test_multiply():
    from src.calculator import multiply
    assert multiply(2, 3) == 6
"""
            )

            # Test configuration
            (root / "pytest.ini").write_text(
                """
[pytest]
testpaths = tests
minversion = 6.0
"""
            )

            # Coverage config
            (root / ".coveragerc").write_text(
                """
[run]
source = src
omit = */tests/*

[report]
fail_under = 80
"""
            )

            yield root

    async def test_request_with_files(self, tool):
        """Test that request can include file paths for analysis"""
        request = TestGuardRequest(
            prompt="Should I adjust the test expectation to match the current output?",
            files=["src/calculator.py", "tests/test_calculator.py"],
        )

        assert request.files is not None
        assert len(request.files) == 2

    async def test_request_with_test_context(self, tool):
        """Test request with test-specific context options"""
        request = TestGuardRequest(
            prompt="Is it okay to lower coverage threshold?", include_test_context=True, check_coverage=True
        )

        assert request.include_test_context is True
        assert request.check_coverage is True

    async def test_backwards_compatibility(self, tool):
        """Test that old requests without file context still work"""
        request = TestGuardRequest(prompt="Can I skip this failing test?")

        assert request.files is None
        assert request.include_test_context is False

    async def test_detect_expectation_adjustment(self, tool, temp_project):
        """Test detection of test expectation adjustments"""
        request = TestGuardRequest(
            prompt="The test expects 5 but gets -1, should I change the assertion?",
            files=[str(temp_project / "src" / "calculator.py"), str(temp_project / "tests" / "test_calculator.py")],
        )

        with patch("tools.testguard.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_relevant_files.return_value = {
                "files": [
                    {"path": "src/calculator.py", "content": "def add(a, b): return a - b  # Bug!"},
                    {"path": "tests/test_calculator.py", "content": "assert add(2, 3) == -1  # Was: == 5"},
                ],
                "total_tokens": 50,
            }

            prompt = await tool.prepare_prompt(request)

            # Should include file context showing the manipulation
            assert "calculator.py" in prompt or "test_calculator.py" in prompt
            mock_instance.get_relevant_files.assert_called()

    async def test_detect_coverage_threshold_manipulation(self, tool, temp_project):
        """Test detection of coverage threshold lowering"""
        request = TestGuardRequest(
            prompt="Coverage is at 75%, can I lower the threshold to 70%?",
            files=[str(temp_project / ".coveragerc")],
            check_coverage=True,
        )

        with patch("tools.testguard.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_relevant_files.return_value = {
                "files": [{"path": ".coveragerc", "content": "[report]\nfail_under = 80"}],
                "total_tokens": 20,
            }

            prompt = await tool.prepare_prompt(request)

            # Should show current coverage threshold
            assert "80" in prompt or "coverage" in prompt.lower()

    async def test_auto_find_test_files(self, tool, temp_project):
        """Test automatic discovery of test files for implementation"""
        request = TestGuardRequest(
            prompt="Should I modify the test for this function?",
            files=[str(temp_project / "src" / "calculator.py")],
            include_related=True,
        )

        with patch("tools.testguard.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.find_related_files.return_value = [str(temp_project / "tests" / "test_calculator.py")]
            mock_instance.get_relevant_files.return_value = {
                "files": [
                    {"path": "src/calculator.py", "content": "..."},
                    {"path": "tests/test_calculator.py", "content": "..."},
                ],
                "total_tokens": 100,
            }

            await tool.prepare_prompt(request)

            # Should find related test files
            mock_instance.find_related_files.assert_called()

    async def test_test_context_gathering(self, tool, temp_project):
        """Test gathering comprehensive test context"""
        request = TestGuardRequest(prompt="Review test methodology", include_test_context=True)

        with patch("tools.testguard.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_test_context.return_value = {
                "test_files": ["tests/test_calculator.py"],
                "test_configs": ["pytest.ini"],
                "coverage_config": ".coveragerc",
                "test_patterns": ["test_*.py"],
            }

            await tool.prepare_prompt(request)

            # Should gather test context
            mock_instance.get_test_context.assert_called()

    async def test_detect_test_skip_pattern(self, tool):
        """Test detection of test skipping anti-pattern"""
        request = TestGuardRequest(
            prompt="Can I add @pytest.skip to this failing test?", files=["tests/test_failing.py"]
        )

        with patch("tools.testguard.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_relevant_files.return_value = {
                "files": [
                    {
                        "path": "tests/test_failing.py",
                        "content": "@pytest.skip('TODO: fix later')\ndef test_important():",
                    }
                ],
                "total_tokens": 30,
            }

            prompt = await tool.prepare_prompt(request)

            # Should detect skip pattern
            assert "skip" in prompt.lower()

    async def test_compare_test_and_implementation_changes(self, tool, temp_project):
        """Test comparing test changes with implementation changes"""
        request = TestGuardRequest(
            prompt="I changed the test assertion, is this okay?",
            files=[str(temp_project / "src" / "calculator.py"), str(temp_project / "tests" / "test_calculator.py")],
            compare_changes=True,
        )

        with patch("tools.testguard.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_relevant_files.return_value = {
                "files": [
                    {"path": "src/calculator.py", "content": "def add(a, b): return a - b  # Bug", "changed": False},
                    {
                        "path": "tests/test_calculator.py",
                        "content": "assert add(2, 3) == -1  # Changed from == 5",
                        "changed": True,
                    },
                ],
                "total_tokens": 60,
            }

            prompt = await tool.prepare_prompt(request)

            # Should note that test changed but not implementation
            assert "changed" in prompt.lower() or "calculator" in prompt

    async def test_validation_with_file_context(self, tool):
        """Test that validation uses file context effectively"""
        request = TestGuardRequest(prompt="Should I lower the test coverage requirement?", files=[".coveragerc"])

        with patch("tools.testguard.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_relevant_files.return_value = {
                "files": [{"path": ".coveragerc", "content": "fail_under = 80"}],
                "total_tokens": 20,
            }

            # Test that prepare_prompt calls the file processor
            prompt = await tool.prepare_prompt(request)

            # Verify context was used
            mock_instance.get_relevant_files.assert_called()

            # Verify the prompt includes file context
            assert ".coveragerc" in prompt
            assert "FILE CONTEXT" in prompt

    async def test_handle_missing_test_files(self, tool):
        """Test handling when test files are missing"""
        request = TestGuardRequest(prompt="Check test coverage", files=["nonexistent_test.py"])

        with patch("tools.testguard.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_relevant_files.return_value = {
                "files": [{"path": "nonexistent_test.py", "error": "File not found"}],
                "total_tokens": 0,
            }

            prompt = await tool.prepare_prompt(request)

            # Should handle gracefully
            assert "error" in prompt.lower() or "not found" in prompt.lower()

    async def test_security_no_system_files(self, tool):
        """Test that system files cannot be accessed"""
        request = TestGuardRequest(prompt="Check test", files=["/etc/passwd", "~/.ssh/config"])

        with patch("tools.testguard.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_relevant_files.return_value = {
                "files": [],
                "total_tokens": 0,
                "errors": ["Security: Access denied"],
            }

            prompt = await tool.prepare_prompt(request)

            # Should not include system files
            assert "/etc/passwd" not in prompt or "denied" in prompt

    async def test_detect_workaround_pattern(self, tool):
        """Test detection of workaround patterns in tests"""
        request = TestGuardRequest(
            prompt="I'll add a try/except to make the test pass", files=["tests/test_workaround.py"]
        )

        with patch("tools.testguard.FileContextProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_processor.return_value = mock_instance
            mock_instance.get_relevant_files.return_value = {
                "files": [
                    {
                        "path": "tests/test_workaround.py",
                        "content": """
def test_function():
    try:
        result = function_under_test()
        assert result == expected
    except:
        # Workaround: just pass if it fails
        pass
""",
                    }
                ],
                "total_tokens": 40,
            }

            prompt = await tool.prepare_prompt(request)

            # Should identify workaround pattern
            assert "workaround" in prompt.lower() or "try" in prompt
