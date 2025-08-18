# HestAI MCP Server Rebranding Transformation Plan

**WORKSPACE_ARCHITECT - B1_02 IMPLEMENTATION STRATEGY**

## TRANSFORMATION MATRIX

### PHASE 1: Configuration & Infrastructure Layer
**Priority: CRITICAL - Foundation must be stable**

#### 1.1 Package Identity Transformation
- `zen-mcp-server` → `hestai-mcp-server` (58 occurrences)
- `.zen_venv` → `.hestai_venv` (47 occurrences) 
- `zen-mcp-server` wrapper script → `hestai-mcp-server`

#### 1.2 Repository URL Transformation  
- `BeehiveInnovations/zen-mcp-server` → `elevanaltd/hestai-mcp-server`
- All GitHub raw URLs, issue templates, workflows
- Docker registry references

#### 1.3 Docker Infrastructure
- Image names: `zen-mcp-server:latest` → `hestai-mcp-server:latest`
- Container names: `zen-mcp-server` → `hestai-mcp-server`
- Docker labels and metadata

### PHASE 2: Documentation Layer  
**Priority: HIGH - User-facing content**

#### 2.1 User Documentation
- README.md installation instructions
- Setup guides (WSL, Docker, Gemini)
- Configuration examples

#### 2.2 Internal Documentation
- CLAUDE.md development guides
- Tool documentation files
- Troubleshooting guides

### PHASE 3: Codebase Layer
**Priority: MEDIUM - Internal references**

#### 3.1 Python Code References
- Import paths and module references
- Logging contexts and error messages
- Test file assertions

#### 3.2 Configuration Files
- pyproject.toml package definition
- Docker compose service definitions
- Environment file examples

## TRANSFORMATION EXECUTION PROTOCOL

### CONTEXT-AWARE REPLACEMENT PATTERNS

#### Pattern 1: Package Names
```bash
# Direct package name references
zen-mcp-server → hestai-mcp-server
```

#### Pattern 2: Virtual Environment
```bash
# Virtual environment directory
.zen_venv → .hestai_venv
```

#### Pattern 3: Repository URLs
```bash
# GitHub repository references
BeehiveInnovations/zen-mcp-server → elevanaltd/hestai-mcp-server
```

#### Pattern 4: Docker References
```bash
# Docker image and container names
zen-mcp-server:latest → hestai-mcp-server:latest
container_name: zen-mcp-server → container_name: hestai-mcp-server
```

#### Pattern 5: Executable Scripts
```bash
# Wrapper script names
zen-mcp-server → hestai-mcp-server
zen-mcp-server.cmd → hestai-mcp-server.cmd
```

## PRESERVATION PROTOCOLS

### CRITICAL PRESERVATION REQUIREMENTS
1. **Functional Behavior**: No logic changes during transformation
2. **Git History**: Maintain commit history and blame information  
3. **Configuration Compatibility**: Existing user configs should work with path updates
4. **Test Integrity**: All tests must pass post-transformation

### VERIFICATION CHECKPOINTS
1. **Post-Pattern Application**: Grep validation for missed occurrences
2. **Syntax Validation**: Python import checks, Docker build tests
3. **Functional Testing**: Integration test suite execution
4. **Documentation Coherence**: Cross-reference link validation

## IMPLEMENTATION SEQUENCE

### Sequence 1: Infrastructure Foundation
1. Update package definition (pyproject.toml)
2. Transform Docker configurations
3. Update wrapper scripts and executables

### Sequence 2: Configuration Layer  
1. Update environment and configuration examples
2. Transform CI/CD workflows
3. Update development scripts

### Sequence 3: Documentation Layer
1. Update user-facing documentation
2. Transform internal development guides
3. Update tool-specific documentation

### Sequence 4: Codebase Integration
1. Update Python code references
2. Transform test assertions and validations
3. Update logging and error contexts

## ROLLBACK STRATEGY
- Git branch protection before each phase
- Incremental commits allowing selective rollback
- Test validation gates preventing broken state progression

## SUCCESS CRITERIA
1. Zero grep matches for old patterns in critical contexts
2. 100% test suite passing
3. Docker build and run successful
4. Documentation cross-references validated
5. No functional behavior changes detected