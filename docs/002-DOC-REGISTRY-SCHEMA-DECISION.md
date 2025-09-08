# Registry Tool MCP Schema Architectural Decision Record

## Date: 2025-09-04

## Status: APPROVED

## Context
The registry tool's MCP interface was incomplete - only exposing the 'action' parameter while the execute() method required additional parameters for each action type. This prevented subagents from properly interacting with the registry through MCP.

## Decision
Implement a phased approach to fix the MCP schema:

### Phase 1 (Immediate): Expose All Parameters
Add all parameters to get_tool_fields() with descriptive documentation indicating which are required for each action.

### Phase 2 (Enhancement): Conditional Schema  
Implement proper JSON Schema oneOf pattern for action-specific parameter validation.

## Rationale
Critical-Engineer analysis identified this as a "liar schema" problem where the interface contract doesn't match the implementation. The proper solution uses JSON Schema's conditional capabilities for:
- Machine-readable contracts
- Client-side validation  
- Single source of truth
- MCP protocol compliance

## Architectural Validation
```
Critical-Engineer: consulted for Tool Interface Contract and MCP schema design
Result: APPROVED with strong recommendation for conditional schema approach
Key Finding: "The core logic is sound. The problem is purely at the API contract layer."
```

## Implementation Impact
- **Backward Compatibility**: Phase 1 maintains compatibility while exposing needed fields
- **Subagent Functionality**: Enables testguard, critical-engineer, and other tools to make registry calls
- **Future Enhancement**: Phase 2 will implement the architecturally correct conditional schema

## Approval
This change is architecturally sound and necessary for system functionality. The critical-engineer's comprehensive analysis provides sufficient technical validation for implementation.