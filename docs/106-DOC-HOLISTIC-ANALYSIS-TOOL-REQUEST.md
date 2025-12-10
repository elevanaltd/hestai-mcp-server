# Holistic Analysis Tool Request

## Overview

Request for a new MCP tool that provides comprehensive codebase analysis and "bigger picture" insights using repomix integration and holistic context aggregation.

## Problem Statement

Current HestAI orchestrator lacks comprehensive codebase synthesis capability for:
- **Architectural overview** for complex codebases
- **Cross-cutting impact analysis** for changes
- **Onboarding acceleration** for new developers
- **Strategic planning** with full context awareness

## Proposed Solution

### Tool Specification
- **Name**: `holistic_analysis`
- **Type**: Simple Tool (single request → analysis → formatted output)
- **Integration**: Leverages existing repomix MCP capabilities
- **Interface**: `mcp__hestai__holistic_analysis`

### Core Functionality
```python
def holistic_analysis(
    directory: str,
    focus_areas: List[str] = None,  # architecture, performance, security, quality
    analysis_depth: str = "standard",  # surface, standard, deep
    output_format: str = "actionable"  # summary, detailed, actionable
) -> HolisticAnalysisResponse
```

### Implementation Approach

**Architecture Decision**: Implement as composable tool rather than separate agent to preserve HestAI's "one brain, many limbs" principle and avoid split-brain orchestration risks.

#### Phase 1: Lightweight Tool
- Directory structure analysis
- Basic pattern recognition
- Integration with existing repomix capabilities
- Performance-conscious implementation with caching

#### Phase 2: Enhanced Context
- Cross-cutting dependency analysis
- Architectural insight synthesis
- Performance bottleneck identification
- Security posture assessment

## Technical Specifications

### Input Schema
```python
{
    "directory": {
        "type": "string",
        "description": "Absolute path to directory for analysis"
    },
    "focus_areas": {
        "type": "array",
        "items": {"enum": ["architecture", "performance", "security", "quality", "general"]},
        "description": "Specific analysis focus areas"
    },
    "analysis_depth": {
        "enum": ["surface", "standard", "deep"],
        "default": "standard",
        "description": "Depth of analysis to perform"
    },
    "output_format": {
        "enum": ["summary", "detailed", "actionable"],
        "default": "actionable",
        "description": "Format for analysis output"
    }
}
```

### Output Schema
```python
{
    "status": "success",
    "analysis": {
        "overview": "High-level codebase summary",
        "architecture_insights": "Key architectural patterns and decisions",
        "cross_cutting_concerns": "Dependencies and impact analysis",
        "recommendations": "Actionable improvement suggestions",
        "metrics": {
            "complexity_score": "Numerical assessment",
            "maintainability": "Rating with justification",
            "test_coverage_estimate": "Coverage analysis"
        }
    },
    "evidence": {
        "files_analyzed": "List of key files examined",
        "patterns_detected": "Specific patterns found",
        "tooling_identified": "Build/test/deployment tools detected"
    }
}
```

## Implementation Strategy

### Integration Points
1. **Repomix Integration**: Use `mcp__repomix__pack_codebase` for context gathering
2. **Context Processing**: Leverage existing HestAI context management patterns
3. **Analysis Engine**: Implement using proven Simple Tool architecture
4. **Caching Strategy**: File-based caching for performance optimization

### Performance Considerations
- **Selective Analysis**: Focus on key files rather than full codebase processing
- **Incremental Processing**: Cache analysis results for repeated requests
- **Token Budget Management**: Implement smart sampling for large codebases
- **Timeout Handling**: Graceful degradation for complex repositories

### Risk Mitigation
- **Scope Creep Prevention**: Clear boundaries vs existing orchestrator capabilities
- **Performance Bottlenecks**: Robust caching and incremental analysis patterns
- **Maintenance Overhead**: Minimal implementation using existing infrastructure

## Expert Consensus Assessment

### Technical Feasibility
✅ **Confirmed achievable** with existing HestAI infrastructure
- No fundamental blockers identified
- 1-2 engineer-weeks estimated for core functionality
- Leverages proven repomix and Simple Tool patterns

### Architectural Alignment
✅ **Tool-based approach preserves HestAI design principles**
- Avoids "split-brain" orchestration risks
- Maintains single authority model
- Enables composable functionality

### User Value Validation
✅ **Strong demand for comprehensive codebase insights**
- Addresses legitimate gap in current capabilities
- Clear use cases for architectural review and onboarding
- Complementary to existing orchestrator functions

## Recommendation

**PROCEED** with tool-based implementation using staged approach:

### Phase 1: Minimal Viable Tool (2 weeks)
- Basic directory analysis with repomix integration
- Simple architectural pattern detection
- Performance-conscious implementation

### Phase 2: Enhanced Analysis (4 weeks)
- Cross-cutting dependency analysis
- Security and performance insights
- Comprehensive caching strategy

### Success Metrics
- Adoption rate by HestAI users
- Performance benchmarks (sub-30s for medium repos)
- User feedback on insight quality
- Integration smoothness with existing workflows

## Implementation Notes

### Base Class Selection
Use `SimpleTool` architecture for clean request/response pattern:
```python
from tools.simple.base import SimpleTool

class HolisticAnalysisTool(SimpleTool):
    def get_name(self) -> str:
        return "holistic_analysis"
```

### Testing Strategy
- **Simulator Tests**: Validate MCP communication and AI model interactions
- **Performance Tests**: Benchmark with various repository sizes
- **Integration Tests**: Ensure smooth orchestrator integration

### Documentation Requirements
- Tool usage guide in `/docs/tools/`
- API documentation with examples
- Performance characteristics and limitations
- Integration patterns for orchestrator use

---

**Status**: Ready for Implementation Review
**Priority**: Medium-High (addresses legitimate capability gap)
**Risk Level**: Low (leverages proven patterns)
**Estimated Effort**: 2-4 engineer-weeks staged implementation
