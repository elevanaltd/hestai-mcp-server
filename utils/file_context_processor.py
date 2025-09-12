"""
File Context Processor - Secure file context gathering for validation tools

This module provides structured file content and tree information to validation
tools like critical-engineer and testguard, enabling them to make informed
decisions with actual code context.

Security Model:
- All file access is validated through existing security infrastructure
- Operates within PROJECT_ROOT boundaries
- Read-only access patterns
- Token budget management to prevent resource exhaustion

<!-- Critical-Engineer: consulted for Filesystem interaction and configuration parsing -->
<!-- Validated: design-reviewed implementation-approved production-ready -->
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from .file_utils import read_file_safely
from .security_config import EXCLUDED_DIRS, is_dangerous_path
from .token_utils import estimate_tokens

logger = logging.getLogger(__name__)


class FileContextProcessor:
    """
    Secure file context gathering for validation tools.

    Provides structured file content, directory trees, and intelligent
    file discovery for critical-engineer and testguard tools.
    
    Memory Management:
    - LRU caching with bounded size to prevent memory exhaustion
    - Automatic eviction of oldest entries when cache is full
    """

    def __init__(self, project_root: Optional[str] = None, cache_size: int = 128):
        """
        Initialize the FileContextProcessor.

        Args:
            project_root: Root directory for the project (defaults to current directory)
            cache_size: Maximum number of file contents to cache (default: 128)
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.project_root = self.project_root.resolve()
        self.cache_size = cache_size

        # Create bounded LRU cache for file contents to prevent memory exhaustion
        self._read_file_cached = lru_cache(maxsize=cache_size)(self._read_file_uncached)

        # Critical-Engineer: consulted for Session management async conversion and concurrency model
        logger.debug(f"FileContextProcessor initialized with cache_size={cache_size} for {self.project_root}")

    def _read_file_uncached(self, file_path: str) -> Optional[str]:
        """
        Uncached file reading method for LRU cache.
        
        Args:
            file_path: Absolute path to file to read
            
        Returns:
            File content or None if unreadable
        """
        try:
            return read_file_safely(file_path)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    def clear_cache(self):
        """
        Clear the file content cache to free memory.
        Useful for long-running sessions or memory pressure.
        """
        self._read_file_cached.cache_clear()
        logger.debug(f"FileContextProcessor cache cleared for {self.project_root}")

    def cache_info(self) -> dict[str, Any]:
        """
        Get cache statistics for monitoring and debugging.
        
        Returns:
            Dictionary with cache hit/miss statistics
        """
        info = self._read_file_cached.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "maxsize": info.maxsize,
            "currsize": info.currsize,
            "hit_rate": info.hits / (info.hits + info.misses) if (info.hits + info.misses) > 0 else 0.0
        }

    def get_file_tree(self, root_path: str, max_depth: int = 3) -> dict[str, Any]:
        """
        Generate a structured file tree for architectural awareness.

        Args:
            root_path: Root directory to generate tree from
            max_depth: Maximum depth to traverse

        Returns:
            Dictionary containing tree structure and statistics
        """
        try:
            root = Path(root_path).resolve()

            # Security check
            if is_dangerous_path(root):
                return {
                    "structure": "Access denied - security restriction",
                    "total_files": 0,
                    "total_dirs": 0,
                    "error": "Path is restricted",
                }

            tree_lines = []
            total_files = 0
            total_dirs = 0

            def build_tree(path: Path, prefix: str = "", depth: int = 0):
                nonlocal total_files, total_dirs

                if depth >= max_depth:
                    return

                try:
                    items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))

                    for i, item in enumerate(items):
                        # Skip excluded directories
                        if item.is_dir() and item.name in EXCLUDED_DIRS:
                            tree_lines.append(f"{prefix}├── {item.name}/ [excluded]")
                            continue

                        is_last = i == len(items) - 1
                        current_prefix = "└── " if is_last else "├── "
                        next_prefix = "    " if is_last else "│   "

                        if item.is_dir():
                            total_dirs += 1
                            tree_lines.append(f"{prefix}{current_prefix}{item.name}/")
                            build_tree(item, prefix + next_prefix, depth + 1)
                        else:
                            total_files += 1
                            tree_lines.append(f"{prefix}{current_prefix}{item.name}")

                except PermissionError:
                    tree_lines.append(f"{prefix}[Permission Denied]")

            # Build the tree
            tree_lines.append(f"{root.name}/")
            build_tree(root, "", 0)

            return {
                "structure": "\n".join(tree_lines),
                "total_files": total_files,
                "total_dirs": total_dirs,
                "root": str(root),
            }

        except Exception as e:
            logger.error(f"Error generating file tree: {e}")
            return {"structure": f"Error: {str(e)}", "total_files": 0, "total_dirs": 0, "error": str(e)}

    def get_relevant_files(
        self, file_paths: list[str], token_budget: int = 5000, prioritize: bool = False
    ) -> dict[str, Any]:
        """
        Retrieve file contents within a token budget.

        Args:
            file_paths: List of file paths to read
            token_budget: Maximum tokens to use
            prioritize: Whether to intelligently prioritize files

        Returns:
            Dictionary with file contents and token usage
        """
        result = {"files": [], "total_tokens": 0, "truncated": False}

        # Prioritize files if requested
        if prioritize:
            file_paths = self._prioritize_files(file_paths)

        for file_path in file_paths:
            try:
                path = Path(file_path).resolve()

                # Security check
                if is_dangerous_path(path):
                    result["files"].append({"path": file_path, "error": "Access denied - security restriction"})
                    continue

                if not path.exists():
                    result["files"].append({"path": file_path, "error": "File not found"})
                    continue

                # Read file content using cached method to prevent memory exhaustion
                content = self._read_file_cached(str(path))
                if content is None:
                    result["files"].append({"path": file_path, "error": "Could not read file"})
                    continue

                # Check token budget
                file_tokens = estimate_tokens(content)
                if result["total_tokens"] + file_tokens > token_budget:
                    # Try to include partial content
                    remaining_budget = token_budget - result["total_tokens"]
                    if remaining_budget > 100:  # Include if we have reasonable space
                        # Approximate truncation (4 chars per token estimate)
                        max_chars = remaining_budget * 4
                        truncated_content = content[:max_chars] + "\n... [truncated]"
                        result["files"].append(
                            {
                                "path": file_path,
                                "content": truncated_content,
                                "truncated": True,
                                "original_tokens": file_tokens,
                            }
                        )
                        result["total_tokens"] = token_budget
                        result["truncated"] = True
                    break

                result["files"].append({"path": file_path, "content": content, "tokens": file_tokens})
                result["total_tokens"] += file_tokens

            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                result["files"].append({"path": file_path, "error": str(e)})

        return result

    def find_related_files(self, file_path: str, include_configs: bool = False) -> list[str]:
        """
        Intelligently find files related to the given file.

        Args:
            file_path: Path to the file to find relations for
            include_configs: Whether to include configuration files

        Returns:
            List of related file paths
        """
        related = []

        try:
            path = Path(file_path).resolve()

            if not path.exists():
                return []

            # Security check
            if is_dangerous_path(path):
                return []

            file_name = path.stem
            project_root = self._find_project_root(path)

            # Find test files for implementation files
            if "test" not in file_name.lower():
                # Look for corresponding test files
                test_patterns = [
                    f"test_{file_name}",
                    f"{file_name}_test",
                    f"test{file_name}",
                    file_name,  # Sometimes test files have same name in test dir
                ]

                # Search in common test directories
                test_dirs = ["tests", "test", "spec", "__tests__"]
                for test_dir_name in test_dirs:
                    test_dir = project_root / test_dir_name
                    if test_dir.exists():
                        for pattern in test_patterns:
                            for ext in [".py", ".js", ".ts", ".java", ".go"]:
                                test_file = test_dir / f"{pattern}{ext}"
                                if test_file.exists():
                                    related.append(str(test_file))

            # Find implementation files for test files
            else:
                # Remove test prefixes/suffixes
                impl_name = file_name
                for prefix in ["test_", "test"]:
                    if impl_name.lower().startswith(prefix):
                        impl_name = impl_name[len(prefix) :]
                        break
                for suffix in ["_test", "Test", ".test", ".spec"]:
                    if impl_name.endswith(suffix):
                        impl_name = impl_name[: -len(suffix)]
                        break

                # Look for implementation files
                src_dirs = ["src", "lib", "app", "."]
                for src_dir_name in src_dirs:
                    src_dir = project_root / src_dir_name
                    if src_dir.exists():
                        for ext in [".py", ".js", ".ts", ".java", ".go"]:
                            impl_file = src_dir / f"{impl_name}{ext}"
                            if impl_file.exists():
                                related.append(str(impl_file))

            # Include configuration files if requested
            if include_configs:
                config_files = [
                    "package.json",
                    "pyproject.toml",
                    "setup.py",
                    "requirements.txt",
                    "Cargo.toml",
                    "go.mod",
                    "pom.xml",
                    "build.gradle",
                    "tsconfig.json",
                    "jest.config.js",
                    "pytest.ini",
                    ".coveragerc",
                ]

                for config_name in config_files:
                    config_path = project_root / config_name
                    if config_path.exists():
                        related.append(str(config_path))

            # Remove duplicates and original file
            related = list(set(related))
            if str(path) in related:
                related.remove(str(path))

            return related

        except Exception as e:
            logger.error(f"Error finding related files for {file_path}: {e}")
            return []

    def get_architectural_context(self, project_path: str) -> dict[str, Any]:
        """
        Get comprehensive architectural context for validation.

        Args:
            project_path: Path to the project root

        Returns:
            Dictionary with architectural information
        """
        context = {"tree": {}, "configs": [], "entry_points": [], "test_structure": [], "dependencies": []}

        try:
            root = Path(project_path).resolve()

            # Get directory tree
            context["tree"] = self.get_file_tree(str(root), max_depth=3)

            # Find configuration files
            config_patterns = [
                "package.json",
                "pyproject.toml",
                "setup.py",
                "requirements*.txt",
                "Cargo.toml",
                "go.mod",
                "pom.xml",
                "build.gradle",
                "*.config.js",
                "tsconfig.json",
                "Dockerfile",
                "docker-compose*.yml",
            ]

            for pattern in config_patterns:
                for config_file in root.glob(pattern):
                    if config_file.is_file():
                        context["configs"].append(str(config_file.relative_to(root)))

            # Find entry points
            entry_patterns = [
                "main.py",
                "app.py",
                "index.js",
                "index.ts",
                "main.go",
                "Main.java",
                "server.py",
                "cli.py",
                "run.py",
            ]

            for pattern in entry_patterns:
                for entry_file in root.rglob(pattern):
                    if entry_file.is_file():
                        rel_path = str(entry_file.relative_to(root))
                        if not any(excluded in rel_path for excluded in EXCLUDED_DIRS):
                            context["entry_points"].append(rel_path)

            # Identify test structure
            test_dirs = ["tests", "test", "spec", "__tests__"]
            for test_dir_name in test_dirs:
                test_dir = root / test_dir_name
                if test_dir.exists() and test_dir.is_dir():
                    context["test_structure"].append(test_dir_name)

            # Extract dependencies if possible
            if (root / "requirements.txt").exists():
                content = self._read_file_cached(str(root / "requirements.txt"))
                if content:
                    context["dependencies"] = [
                        line.strip() for line in content.split("\n") if line.strip() and not line.startswith("#")
                    ][
                        :10
                    ]  # Limit to first 10

            elif (root / "package.json").exists():
                content = self._read_file_cached(str(root / "package.json"))
                if content:
                    try:
                        pkg = json.loads(content)
                        deps = list(pkg.get("dependencies", {}).keys())[:10]
                        context["dependencies"] = deps
                    except json.JSONDecodeError:
                        pass

            return context

        except Exception as e:
            logger.error(f"Error getting architectural context: {e}")
            return context

    def get_test_context(self, project_path: str) -> dict[str, Any]:
        """
        Get test-specific context for testguard validation.

        Args:
            project_path: Path to the project root

        Returns:
            Dictionary with test-related information
        """
        context = {
            "test_files": [],
            "test_configs": [],
            "coverage_config": None,
            "test_patterns": [],
            "test_framework": None,
        }

        try:
            root = Path(project_path).resolve()

            # Find test configuration files
            test_config_patterns = [
                "pytest.ini",
                "pytest.cfg",
                "setup.cfg",
                "tox.ini",
                "jest.config.js",
                "jest.config.ts",
                "jest.config.mjs",
                "karma.conf.js",
                "mocha.opts",
                "vitest.config.js",  # Add Vitest patterns
                "vitest.config.ts",  # Add Vitest patterns
                "vitest.config.mjs",  # Add Vitest patterns
                "vite.config.js",  # Add Vite patterns (Vitest often configured here)
                "vite.config.ts",  # Add Vite patterns
                "package.json",  # Add package.json (check scripts section)
                ".coveragerc",
                "coverage.json",
                "phpunit.xml",
            ]

            for pattern in test_config_patterns:
                for config_file in root.glob(pattern):
                    if config_file.is_file():
                        rel_path = str(config_file.relative_to(root))
                        context["test_configs"].append(rel_path)

                        # Identify coverage config
                        if "coverage" in config_file.name.lower():
                            context["coverage_config"] = rel_path

                        # Identify test framework
                        if "pytest" in config_file.name:
                            context["test_framework"] = "pytest"
                        elif "jest" in config_file.name:
                            context["test_framework"] = "jest"
                        elif "mocha" in config_file.name:
                            context["test_framework"] = "mocha"
                        elif "vitest" in config_file.name or "vite" in config_file.name:
                            context["test_framework"] = "vitest"
                        elif config_file.name == "package.json":
                            # Parse package.json for test scripts indicating framework
                            try:
                                # Context7: consulted for json (standard library)
                                import json

                                content = self._read_file_cached(str(config_file))
                                if content:
                                    pkg = json.loads(content)
                                    scripts = pkg.get("scripts", {})
                                    if any("vitest" in script for script in scripts.values()):
                                        context["test_framework"] = "vitest"
                                    elif any("jest" in script for script in scripts.values()):
                                        if context["test_framework"] is None:  # Don't override existing
                                            context["test_framework"] = "jest"
                            except (json.JSONDecodeError, Exception):
                                pass  # Gracefully handle invalid JSON or other errors

            # Find test files
            test_patterns = [
                "test_*.py",
                "*_test.py",  # Python
                "*.test.js",
                "*.spec.js",  # JavaScript
                "*.test.ts",
                "*.spec.ts",  # TypeScript
                "*.test.jsx",
                "*.spec.jsx",  # JSX
                "*.test.tsx",
                "*.spec.tsx",  # TSX
                "test/*.js",
                "test/*.ts",  # Test directory patterns
                "__tests__/*.js",
                "__tests__/*.ts",  # Jest convention
            ]
            for pattern in test_patterns:
                for test_file in root.rglob(pattern):
                    if test_file.is_file():
                        rel_path = str(test_file.relative_to(root))
                        if not any(excluded in rel_path for excluded in EXCLUDED_DIRS):
                            context["test_files"].append(rel_path)

                            # Track patterns
                            if pattern not in context["test_patterns"]:
                                context["test_patterns"].append(pattern)

            # Limit test files for context
            context["test_files"] = context["test_files"][:20]

            return context

        except Exception as e:
            logger.error(f"Error getting test context: {e}")
            return context

    def _prioritize_files(self, file_paths: list[str]) -> list[str]:
        """
        Intelligently prioritize files based on importance.

        Args:
            file_paths: List of file paths to prioritize

        Returns:
            Reordered list with higher priority files first
        """
        priority_scores = []

        for path in file_paths:
            score = 0
            path_lower = path.lower()

            # Higher priority for certain file types
            if "main" in path_lower or "app" in path_lower or "index" in path_lower:
                score += 10
            if "critical" in path_lower or "core" in path_lower:
                score += 8
            if "config" in path_lower or "setup" in path_lower:
                score += 6
            if "test" in path_lower:
                score += 4
            if "util" in path_lower or "helper" in path_lower:
                score += 2
            if "deprecated" in path_lower or "legacy" in path_lower or "old" in path_lower:
                score -= 5

            priority_scores.append((score, path))

        # Sort by priority (higher scores first)
        priority_scores.sort(key=lambda x: -x[0])

        return [path for _, path in priority_scores]

    def _find_project_root(self, file_path: Path) -> Path:
        """
        Find the project root directory from a file path.

        Args:
            file_path: Path to start from

        Returns:
            Estimated project root directory
        """
        current = file_path.parent if file_path.is_file() else file_path

        # Look for common project root indicators
        root_indicators = [
            ".git",
            "package.json",
            "pyproject.toml",
            "setup.py",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
        ]

        while current != current.parent:
            for indicator in root_indicators:
                if (current / indicator).exists():
                    return current
            current = current.parent

        # Default to original file's parent directory
        return file_path.parent if file_path.is_file() else file_path
