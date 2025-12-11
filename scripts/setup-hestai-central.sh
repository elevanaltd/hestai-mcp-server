#!/bin/bash
# Setup script for ~/.hestai centralized session repository
# Part of Issue #120: Unified .hestai Architecture
# This script is idempotent - safe to run multiple times

set -e  # Exit on error

HESTAI_DIR="$HOME/.hestai"

echo "🔧 Setting up ~/.hestai centralized session repository..."

# Create base directory if not exists
if [ ! -d "$HESTAI_DIR" ]; then
    echo "  Creating $HESTAI_DIR..."
    mkdir -p "$HESTAI_DIR"
else
    echo "  ✓ $HESTAI_DIR already exists"
fi

# Initialize git repository if not already initialized
if [ ! -d "$HESTAI_DIR/.git" ]; then
    echo "  Initializing git repository..."
    cd "$HESTAI_DIR"
    git init
    git branch -m main
    echo "  ✓ Git repository initialized"
else
    echo "  ✓ Git repository already exists"
fi

# Create .gitignore if not exists
if [ ! -f "$HESTAI_DIR/.gitignore" ]; then
    echo "  Creating .gitignore..."
    cat > "$HESTAI_DIR/.gitignore" << 'EOF'
# Session transcript files (large, frequently changing)
*.jsonl
sessions/archive/*.jsonl

# Temporary files
*.tmp
*.temp
*~
.DS_Store

# Processed inbox items (can be regenerated)
inbox/processed/*

# Keep directory structure
!.gitkeep

# Track important files
!sessions.registry.json
!context/**/*.oct.md
!context/**/*.md
EOF
    echo "  ✓ .gitignore created"
else
    echo "  ✓ .gitignore already exists"
fi

# Create directory structure
echo "  Creating directory structure..."
mkdir -p "$HESTAI_DIR/inbox/pending"
mkdir -p "$HESTAI_DIR/inbox/processed"
mkdir -p "$HESTAI_DIR/sessions"
mkdir -p "$HESTAI_DIR/context"

# Create .gitkeep files to preserve empty directories
touch "$HESTAI_DIR/inbox/pending/.gitkeep"
touch "$HESTAI_DIR/inbox/processed/.gitkeep"
touch "$HESTAI_DIR/sessions/.gitkeep"
touch "$HESTAI_DIR/context/.gitkeep"

echo "  ✓ Directory structure created"

# Check if initial commit exists
cd "$HESTAI_DIR"
if ! git log -1 &>/dev/null; then
    echo "  Creating initial commit..."
    git add -A
    git commit -m "feat(infra): Initialize ~/.hestai as centralized session repository (#120)"
    echo "  ✓ Initial commit created"
else
    echo "  ✓ Git repository already has commits"
fi

echo ""
echo "✅ Setup complete! Structure:"
echo ""
echo "~/.hestai/"
echo "├── .git/                    (Initialized)"
echo "├── .gitignore               (Created)"
echo "├── sessions.registry.json   (Preserved)"
echo "├── inbox/"
echo "│   ├── pending/"
echo "│   └── processed/"
echo "├── sessions/                (For future symlinks)"
echo "└── context/                 (Shared context)"
echo ""
