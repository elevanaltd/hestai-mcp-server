"""
Tests for FileContextProcessor utility

This module tests the file context gathering functionality that enables
validation tools (critical-engineer, testguard) to access relevant files
and directory structures for informed decision-making.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from utils.file_context_processor import FileContextProcessor


class TestFileContextProcessor:
    """Test suite for FileContextProcessor utility"""

    @pytest.fixture
    def processor(self):
        """Create a FileContextProcessor instance for testing"""
        return FileContextProcessor()

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project structure for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Create project structure
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("def hello(): return 'world'")
            (root / "src" / "utils.py").write_text("def helper(): pass")
            
            (root / "tests").mkdir()
            (root / "tests" / "test_main.py").write_text("def test_hello(): assert True")
            
            (root / "docs").mkdir()
            (root / "README.md").write_text("# Test Project")
            
            (root / "package.json").write_text(json.dumps({"name": "test-project"}))
            (root / ".gitignore").write_text("*.pyc\n__pycache__/")
            
            yield root

    def test_get_file_tree_basic(self, processor, temp_project):
        """Test basic file tree generation"""
        tree = processor.get_file_tree(str(temp_project), max_depth=2)
        
        assert tree is not None
        assert "structure" in tree
        assert "total_files" in tree
        assert "total_dirs" in tree
        
        # Check structure includes main directories
        structure = tree["structure"]
        assert "src/" in structure or "src" in str(structure)
        assert "tests/" in structure or "tests" in str(structure)
        assert "docs/" in structure or "docs" in str(structure)

    def test_get_file_tree_max_depth(self, processor, temp_project):
        """Test file tree respects max_depth parameter"""
        # Create deeper structure
        deep_dir = temp_project / "src" / "level1" / "level2" / "level3"
        deep_dir.mkdir(parents=True)
        (deep_dir / "deep.py").write_text("# Deep file")
        
        tree_shallow = processor.get_file_tree(str(temp_project), max_depth=1)
        tree_deep = processor.get_file_tree(str(temp_project), max_depth=4)
        
        # Shallow tree should not include deep files
        assert "level3" not in str(tree_shallow["structure"])
        # Deep tree should include them
        assert tree_deep["total_files"] > tree_shallow["total_files"]

    def test_get_file_tree_excludes_dangerous_paths(self, processor, temp_project):
        """Test that dangerous paths are excluded from tree"""
        # Create potentially dangerous directories
        (temp_project / ".git").mkdir()
        (temp_project / ".git" / "config").write_text("git config")
        (temp_project / "node_modules").mkdir()
        (temp_project / "node_modules" / "package").write_text("module")
        
        tree = processor.get_file_tree(str(temp_project))
        
        # These should be excluded
        structure_str = str(tree["structure"])
        assert ".git" not in structure_str or "[excluded]" in structure_str
        assert "node_modules" not in structure_str or "[excluded]" in structure_str

    def test_get_relevant_files_basic(self, processor, temp_project):
        """Test retrieving specific file contents"""
        files = [
            str(temp_project / "src" / "main.py"),
            str(temp_project / "README.md")
        ]
        
        result = processor.get_relevant_files(files, token_budget=1000)
        
        assert "files" in result
        assert "total_tokens" in result
        assert len(result["files"]) == 2
        
        # Check file contents are included
        main_py = next(f for f in result["files"] if "main.py" in f["path"])
        assert "def hello()" in main_py["content"]

    def test_get_relevant_files_token_budget(self, processor, temp_project):
        """Test that token budget is respected"""
        # Create a large file
        large_content = "x" * 10000  # Large content
        (temp_project / "large.txt").write_text(large_content)
        
        files = [
            str(temp_project / "large.txt"),
            str(temp_project / "src" / "main.py")
        ]
        
        # Very small budget
        result = processor.get_relevant_files(files, token_budget=50)
        
        assert result["total_tokens"] <= 50
        # Should include partial content or skip files
        assert "truncated" in result or len(result["files"]) < 2

    def test_get_relevant_files_missing_file(self, processor, temp_project):
        """Test handling of missing files"""
        files = [
            str(temp_project / "src" / "main.py"),
            str(temp_project / "nonexistent.py")
        ]
        
        result = processor.get_relevant_files(files, token_budget=1000)
        
        # Should handle gracefully
        assert len(result["files"]) >= 1
        # Should note the error
        assert any("error" in f for f in result["files"] if "nonexistent" in f.get("path", ""))

    def test_find_related_files_implementation_to_test(self, processor, temp_project):
        """Test finding test files for implementation files"""
        impl_file = str(temp_project / "src" / "main.py")
        
        related = processor.find_related_files(impl_file)
        
        # Should find the test file
        assert any("test_main.py" in f for f in related)

    def test_find_related_files_test_to_implementation(self, processor, temp_project):
        """Test finding implementation files for test files"""
        test_file = str(temp_project / "tests" / "test_main.py")
        
        related = processor.find_related_files(test_file)
        
        # Should find the implementation file
        assert any("main.py" in f for f in related)

    def test_find_related_files_config_files(self, processor, temp_project):
        """Test finding configuration files"""
        any_file = str(temp_project / "src" / "main.py")
        
        related = processor.find_related_files(any_file, include_configs=True)
        
        # Should include configuration files
        assert any("package.json" in f for f in related)

    def test_find_related_files_nonexistent(self, processor):
        """Test finding related files for nonexistent file"""
        related = processor.find_related_files("/nonexistent/file.py")
        
        # Should return empty list or handle gracefully
        assert isinstance(related, list)
        assert len(related) == 0

    def test_security_path_validation(self, processor):
        """Test that dangerous paths are rejected"""
        dangerous_paths = [
            "/etc/passwd",
            "../../../etc/passwd",
            "~/.ssh/id_rsa"
        ]
        
        for path in dangerous_paths:
            result = processor.get_relevant_files([path], token_budget=1000)
            # Should either exclude or mark as error
            assert len(result["files"]) == 0 or any("error" in f for f in result["files"])

    def test_get_architectural_context(self, processor, temp_project):
        """Test getting architectural context for validation"""
        context = processor.get_architectural_context(str(temp_project))
        
        assert "tree" in context
        assert "configs" in context
        assert "entry_points" in context
        assert "test_structure" in context
        
        # Should identify package.json as config
        assert any("package.json" in c for c in context["configs"])

    def test_get_test_context(self, processor, temp_project):
        """Test getting test-specific context for testguard"""
        # Create test configuration
        (temp_project / "pytest.ini").write_text("[pytest]\ntestpaths = tests")
        (temp_project / ".coveragerc").write_text("[run]\nsource = src")
        
        context = processor.get_test_context(str(temp_project))
        
        assert "test_files" in context
        assert "test_configs" in context
        assert "coverage_config" in context
        assert "test_patterns" in context
        
        # Should find test configuration
        assert any("pytest.ini" in c for c in context["test_configs"])

    @patch("utils.file_context_processor.estimate_tokens")
    def test_token_estimation_accuracy(self, mock_estimate, processor, temp_project):
        """Test that token estimation is used correctly"""
        mock_estimate.return_value = 100
        
        files = [str(temp_project / "src" / "main.py")]
        result = processor.get_relevant_files(files, token_budget=1000)
        
        # Should call token estimation
        mock_estimate.assert_called()
        assert result["total_tokens"] > 0

    def test_intelligent_file_prioritization(self, processor, temp_project):
        """Test that files are intelligently prioritized within budget"""
        # Create files with different priorities
        (temp_project / "critical.py").write_text("# Critical system file")
        (temp_project / "helper.py").write_text("# Helper utility")
        (temp_project / "deprecated.py").write_text("# Deprecated code")
        
        files = [
            str(temp_project / "critical.py"),
            str(temp_project / "helper.py"),
            str(temp_project / "deprecated.py"),
        ]
        
        # Very limited budget
        result = processor.get_relevant_files(files, token_budget=100, prioritize=True)
        
        # Should include critical files first
        if len(result["files"]) > 0:
            assert any("critical" in f["path"] for f in result["files"])