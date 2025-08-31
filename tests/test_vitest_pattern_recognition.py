"""
Test enhanced pattern recognition for Vitest and modern testing frameworks

This test validates the FileContextProcessor's ability to detect:
1. Vitest configuration files
2. Vite configuration files that contain Vitest config
3. Package.json scripts indicating test frameworks
4. Modern test file patterns (JSX, TSX, __tests__)
"""

# Context7: consulted for pytest
# Context7: consulted for pathlib (standard library)
# Context7: consulted for json (standard library)
# Context7: consulted for tempfile (standard library)
# Context7: consulted for utils (internal project module)

import json
import tempfile
from pathlib import Path

from utils.file_context_processor import FileContextProcessor


class TestVitestPatternRecognition:
    """Test suite for enhanced testing framework pattern recognition"""

    def setup_method(self):
        """Set up test context processor"""
        self.processor = FileContextProcessor()

    def test_vitest_config_detection(self):
        """Test detection of Vitest configuration files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create Vitest config files
            (temp_path / "vitest.config.js").write_text("export default { test: {} }")
            (temp_path / "vitest.config.ts").write_text("export default { test: {} }")
            (temp_path / "vitest.config.mjs").write_text("export default { test: {} }")

            context = self.processor.get_test_context(str(temp_path))

            # Should detect all Vitest config files
            assert "vitest.config.js" in context["test_configs"]
            assert "vitest.config.ts" in context["test_configs"]
            assert "vitest.config.mjs" in context["test_configs"]
            assert context["test_framework"] == "vitest"

    def test_vite_config_with_test_detection(self):
        """Test detection of Vite config files that contain test configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create Vite config with test configuration
            vite_config = """
            export default {
              test: {
                environment: 'jsdom'
              }
            }
            """
            (temp_path / "vite.config.js").write_text(vite_config)
            (temp_path / "vite.config.ts").write_text(vite_config)

            context = self.processor.get_test_context(str(temp_path))

            # Should detect Vite configs as test configs when they contain test section
            assert "vite.config.js" in context["test_configs"]
            assert "vite.config.ts" in context["test_configs"]
            assert context["test_framework"] == "vitest"

    def test_package_json_script_detection(self):
        """Test detection of test frameworks from package.json scripts"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create package.json with Vitest scripts
            package_json = {
                "scripts": {"test": "vitest", "test:ui": "vitest --ui", "build": "vite build"},
                "devDependencies": {"vitest": "^1.0.0"},
            }
            (temp_path / "package.json").write_text(json.dumps(package_json, indent=2))

            context = self.processor.get_test_context(str(temp_path))

            # Should detect Vitest from package.json scripts
            assert "package.json" in context["test_configs"]
            assert context["test_framework"] == "vitest"

    def test_modern_test_file_patterns(self):
        """Test detection of modern test file patterns (JSX, TSX, __tests__)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create modern test files
            (temp_path / "Component.test.jsx").write_text("// JSX test")
            (temp_path / "Component.spec.tsx").write_text("// TSX test")

            # Create __tests__ directory structure
            tests_dir = temp_path / "__tests__"
            tests_dir.mkdir()
            (tests_dir / "utils.test.js").write_text("// Jest convention test")
            (tests_dir / "api.test.ts").write_text("// TypeScript test")

            # Create test directory structure
            test_dir = temp_path / "test"
            test_dir.mkdir()
            (test_dir / "integration.js").write_text("// Integration test")
            (test_dir / "unit.ts").write_text("// Unit test")

            context = self.processor.get_test_context(str(temp_path))

            # Should detect all modern test patterns
            test_files = context["test_files"]
            assert any("Component.test.jsx" in f for f in test_files)
            assert any("Component.spec.tsx" in f for f in test_files)
            assert any("__tests__/utils.test.js" in f for f in test_files)
            assert any("__tests__/api.test.ts" in f for f in test_files)
            assert any("test/integration.js" in f for f in test_files)
            assert any("test/unit.ts" in f for f in test_files)

            # Should detect expanded patterns
            patterns = context["test_patterns"]
            expected_patterns = [
                "*.test.jsx",
                "*.spec.tsx",
                "__tests__/*.js",
                "__tests__/*.ts",
                "test/*.js",
                "test/*.ts",
            ]
            for pattern in expected_patterns:
                assert pattern in patterns

    def test_framework_priority_detection(self):
        """Test framework detection priority when multiple configs exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple config files
            (temp_path / "jest.config.js").write_text("module.exports = {}")
            (temp_path / "vitest.config.js").write_text("export default {}")

            context = self.processor.get_test_context(str(temp_path))

            # Should detect both configs
            assert "jest.config.js" in context["test_configs"]
            assert "vitest.config.js" in context["test_configs"]

            # Framework detection should handle multiple frameworks
            # (implementation may choose last detected or have priority rules)
            assert context["test_framework"] in ["jest", "vitest"]

    def test_invalid_package_json_handling(self):
        """Test graceful handling of invalid package.json files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create invalid JSON
            (temp_path / "package.json").write_text("{invalid json")

            # Should not crash
            context = self.processor.get_test_context(str(temp_path))

            # Should still include package.json in configs but not set framework
            assert "package.json" in context["test_configs"]
            # Framework should be None or not set due to parsing error
            assert context["test_framework"] is None or context["test_framework"] != "vitest"

    def test_empty_project_handling(self):
        """Test handling of projects with no test configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Empty directory
            context = self.processor.get_test_context(str(temp_path))

            # Should return empty but valid context
            assert context["test_files"] == []
            assert context["test_configs"] == []
            assert context["test_framework"] is None
            assert context["test_patterns"] == []
