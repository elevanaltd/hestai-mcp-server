"""
Security configuration and path validation constants

This module contains security-related constants and configurations
for file access control.
"""

from pathlib import Path

# Dangerous paths that should never be scanned
# These would give overly broad access and pose security risks
DANGEROUS_PATHS = {
    "/",
    "/etc",
    "/usr",
    "/bin",
    "/var",
    "/root",
    "/home",
    # macOS system paths (which resolve through /private)
    "/private/etc",
    "/private/var/log",
    "/private/var/root",
    "/private/var/audit",
    "/private/var/at",
    "/System",
    "/Library",
    "/Applications",
    # Windows paths
    "C:\\",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Users",
}

# Directories to exclude from recursive file search
# These typically contain generated code, dependencies, or build artifacts
EXCLUDED_DIRS = {
    # Python
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".env",
    "*.egg-info",
    ".eggs",
    "wheels",
    ".Python",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "htmlcov",
    ".coverage",
    "coverage",
    # Node.js / JavaScript
    "node_modules",
    ".next",
    ".nuxt",
    "bower_components",
    ".sass-cache",
    # Version Control
    ".git",
    ".svn",
    ".hg",
    # Build Output
    "build",
    "dist",
    "target",
    "out",
    # IDEs
    ".idea",
    ".vscode",
    ".sublime",
    ".atom",
    ".brackets",
    # Temporary / Cache
    ".cache",
    ".temp",
    ".tmp",
    "*.swp",
    "*.swo",
    "*~",
    # OS-specific
    ".DS_Store",
    "Thumbs.db",
    # Java / JVM
    ".gradle",
    ".m2",
    # Documentation build
    "_build",
    "site",
    # Mobile development
    ".expo",
    ".flutter",
    # Package managers
    "vendor",
}


def is_dangerous_path(path: Path) -> bool:
    """
    Check if a path is in the dangerous paths list.

    Args:
        path: Path to check

    Returns:
        True if the path is dangerous and should not be accessed
    """
    try:
        resolved = path.resolve()
        path_str = str(resolved)

        # Check if path is exactly in dangerous paths
        if path_str in DANGEROUS_PATHS:
            return True

        # Check if path is a child of any dangerous path
        for dangerous_path in DANGEROUS_PATHS:
            if path_str.startswith(dangerous_path + "/") or path_str == dangerous_path:
                return True

        # Check if path is root directory
        if resolved.parent == resolved:
            return True

        return False
    except Exception:
        return True  # If we can't resolve, consider it dangerous
