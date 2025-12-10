# Shared Schema Governance Guidelines

This document establishes the governance model for shared JSON Schema definitions used across HestAI MCP Server tools.

## Overview

The shared schema system consolidates duplicate field definitions across tools to achieve 40-60% token reduction while preserving 100% functional contract integrity. It uses internal JSON Schema `$ref` references to eliminate duplication.

## Governance Model

### Ownership & Responsibility
- **Owner**: Implementation Lead (current maintainer)
- **Review Authority**: Critical Engineer + Technical Architect
- **Change Approval**: Minimum 2 reviewers for any `$defs` modification

### Change Process

#### Adding New Shared Definitions
1. **Threshold**: Field must be duplicated across 3+ tools
2. **Documentation**: Update this file with new definition details
3. **Testing**: Add test case to `test_schema_token_optimization.py`
4. **Review**: Required PR review with impact assessment

#### Modifying Existing Definitions
1. **Impact Analysis**: Document which tools are affected
2. **Backward Compatibility**: Must preserve existing contracts
3. **Migration Plan**: If breaking change needed, provide migration path
4. **Rollback Plan**: Document how to revert changes

#### Breaking Changes Policy
- **Prohibited**: Direct modification that breaks existing tools
- **Required**: Versioning approach (e.g., `temperature_field_v2`)
- **Deprecation**: 2 release cycle notice before removal

## Shared Definition Categories

### Structure
Definitions are organized by logical groups under `$defs`:

```json
"$defs": {
  "commonParameters": {
    "temperature": { ... },
    "thinking_mode": { ... },
    "use_websearch": { ... }
  },
  "sharedModels": {
    "model_field_auto_mode": { ... },
    "model_field_normal_mode": { ... }
  },
  "workflowFields": {
    "step": { ... },
    "findings": { ... },
    "confidence": { ... }
  }
}
```

### Reference Format
- **Common Parameters**: `{"$ref": "#/$defs/commonParameters/temperature"}`
- **Model Fields**: `{"$ref": "#/$defs/sharedModels/model_field_auto_mode"}`
- **Workflow Fields**: `{"$ref": "#/$defs/workflowFields/step"}`

## Current Shared Definitions

### Common Parameters (7-10 tools each)
- `temperature`: Response creativity control (0.0-1.0)
- `thinking_mode`: Reasoning depth levels (minimal|low|medium|high|max)
- `use_websearch`: Web search capability flag
- `continuation_id`: Multi-turn conversation threading
- `use_assistant_model`: Expert analysis enablement flag

### Model Fields (9 tools)
- `model_field_auto_mode`: Full model descriptions + enums for auto mode
- `model_field_normal_mode`: Simplified model selection for normal mode

### Workflow Fields (workflow tools)
- `step`: Current work step description
- `step_number`: Sequential step counter
- `findings`: Investigation findings and insights
- `confidence`: Confidence level enumeration
- `relevant_context`: Methods/functions involved
- `backtrack_from_step`: Revision/rollback capability

## Decision Matrix

### SHARE: When to create shared definition
- ✅ Field appears in 3+ tools with identical schema
- ✅ Description is substantial (>50 characters)
- ✅ Field serves same semantic purpose across tools
- ✅ Low likelihood of tool-specific customization needed

### DON'T SHARE: When to keep local
- ❌ Field appears in <3 tools
- ❌ Tools need different descriptions/constraints
- ❌ Tool-specific validation rules required
- ❌ Field likely to evolve differently per tool

### Examples
**GOOD**: `temperature` field - identical across all workflow tools
**BAD**: `query` field - each tool needs different description

## Risk Mitigation

### Validation Requirements
- All `$ref` changes require integration test validation
- Token reduction must be measured and verified
- MCP client compatibility must be confirmed
- Circular reference safety tests required

### Monitoring
- Track token usage metrics after each change
- Monitor for schema validation failures in production
- Alert on unexpectedly large schema sizes

### Rollback Procedures
1. Revert shared definition changes in `schema_definitions.py`
2. Run token optimization test suite
3. Verify all tools generate valid schemas
4. Deploy and validate MCP client compatibility

## Development Workflow

### Before Making Changes
1. Read this document completely
2. Analyze impact on affected tools
3. Create test cases for new/modified definitions
4. Plan rollback procedure

### During Development
1. Follow structured definition format
2. Use descriptive names and documentation
3. Test with minimal reproduction case first
4. Validate token reduction achieved

### Before Merging
1. Run full test suite including token optimization tests
2. Verify MCP client can resolve all `$ref` references
3. Document changes in PR description
4. Get required reviews from governance team

## Maintenance

### Regular Reviews
- Monthly audit of shared definition usage
- Quarterly assessment of token reduction metrics
- Annual review of governance process effectiveness

### Definition Cleanup
- Remove unused definitions after 2 release cycles
- Consolidate similar definitions when possible
- Update documentation for any changes

## Security Considerations

### DoS Prevention
- Test all schemas with circular reference detection
- Validate parser performance with large `$defs` sections
- Monitor for exponential expansion of nested `$ref`s

### Contract Integrity
- Never modify existing definitions without version bump
- Preserve all functional contracts during optimization
- Validate that model APIs receive correct expanded schemas

## Contacts

- **Technical Questions**: Implementation Lead
- **Architectural Concerns**: Critical Engineer
- **Process Issues**: Technical Architect
- **Emergency Rollback**: All of the above

---

**Last Updated**: 2025-09-14
**Next Review**: Monthly
