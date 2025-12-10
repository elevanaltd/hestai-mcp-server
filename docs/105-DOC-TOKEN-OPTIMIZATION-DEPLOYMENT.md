# Token Optimization Deployment Guide

## Overview
This document describes the deployment strategy for the JSON Schema $ref token optimization feature that reduces MCP tool schema token consumption by ~31.5%.

## Architecture

### Implementation Components
1. **SharedSchemaDefinitions** (`tools/shared/schema_definitions.py`)
   - Central module managing all shared schema definitions
   - Versioned approach (v1) for backward compatibility
   - Consolidates repeated patterns (model enums, thinking modes, etc.)

2. **Canary Test Tool** (`tools/canary_ref_test.py`)
   - Validates MCP client $ref support before production deployment
   - Critical gate ensuring client compatibility

3. **Feature Flag** (`USE_SCHEMA_REFS` environment variable)
   - Defaults to `false` for safety
   - Enables gradual rollout and quick rollback

## Token Savings

### Measured Results
- **Without optimization**: 17,965 tokens
- **With optimization**: 12,302 tokens
- **Reduction**: 5,663 tokens (31.5%)
- **Projected at scale**: ~15,000 tokens saved across all tools

### Key Optimizations
1. **Model enum consolidation**: Single definition referenced everywhere
2. **Common parameters**: temperature, thinking_mode, continuation_id
3. **Workflow fields**: step patterns shared across debug/analyze/planner
4. **Context fields**: files/images arrays with consistent validation

## Deployment Strategy

### Phase 1: Canary Validation (COMPLETED)
```bash
# Test canary tool locally
python test_canary_deployment.py

# Expected output:
# ✓ Canary tool found in registry
# ✓ Schema has correct $ref structure
# ✓ Canary tool executed successfully
# 🎯 CANARY TEST SUCCESSFUL
```

### Phase 2: Staging Deployment
1. Enable in staging environment:
   ```bash
   export USE_SCHEMA_REFS=true
   ```

2. Run comprehensive simulator tests:
   ```bash
   python communication_simulator_test.py --quick
   ```

3. Monitor for any MCP client issues:
   ```bash
   tail -f logs/mcp_server.log | grep -E "(ERROR|$ref|schema)"
   ```

### Phase 3: Production Rollout

#### Step 1: Update Production Config
```bash
# In production .env file
USE_SCHEMA_REFS=true
```

#### Step 2: Deploy with Monitoring
```bash
# Deploy and watch logs
./run-server.sh
tail -f logs/mcp_activity.log
```

#### Step 3: Validation Checklist
- [ ] Canary tool reports $ref support
- [ ] All tools register successfully
- [ ] No schema validation errors in logs
- [ ] Simulator tests pass 100%
- [ ] Token usage reduced by ~30%

### Phase 4: Full Migration
Once validated in production:
1. Remove canary tool (no longer needed)
2. Consider making USE_SCHEMA_REFS default to true
3. Document as standard configuration

## Rollback Plan

If issues occur at any phase:
```bash
# Immediate rollback
export USE_SCHEMA_REFS=false

# Restart server
./run-server.sh

# Verify fallback mode
grep "USE_SCHEMA_REFS" logs/mcp_server.log
```

## Monitoring

### Key Metrics
1. **Token consumption**: Monitor via MCP client metrics
2. **Tool registration**: Check server startup logs
3. **Schema validation**: Watch for JSON Schema errors
4. **Client compatibility**: Track tool execution failures

### Log Patterns to Watch
```bash
# Success indicators
grep "registered with schema" logs/mcp_server.log
grep "ref_support.*VERIFIED" logs/mcp_activity.log

# Error indicators
grep -E "(Invalid schema|$ref.*not.*supported)" logs/mcp_server.log
```

## Governance

### Schema Evolution Process
1. All changes to SharedSchemaDefinitions require:
   - Version bump consideration (v1 → v2)
   - Backward compatibility assessment
   - Test coverage for new definitions

2. Adding new shared definitions:
   ```python
   # In SharedSchemaDefinitions.get_base_definitions()
   "v1": {
       "existingField": {...},
       "newField": {  # Add here
           "type": "string",
           "description": "..."
       }
   }
   ```

3. Using shared definitions in tools:
   ```python
   # In tool's get_input_schema()
   ref_schema = SharedSchemaDefinitions.get_temperature_ref()
   if ref_schema:
       properties["temperature"] = ref_schema
   ```

### Review Requirements
- Changes to schema_definitions.py require code review
- New $ref patterns need canary test validation
- Performance impact assessment for large schemas

## Troubleshooting

### Common Issues

#### MCP Client Doesn't Support $ref
**Symptom**: Tools fail to execute with schema validation errors
**Solution**:
1. Set USE_SCHEMA_REFS=false immediately
2. Check MCP client version/documentation
3. Consider client upgrade or wait for support

#### Partial $ref Support
**Symptom**: Some tools work, others fail
**Solution**:
1. Identify problematic $ref patterns
2. Create tool-specific overrides
3. Report to MCP client maintainers

#### Version Mismatch
**Symptom**: "Unknown $ref path" errors
**Solution**:
1. Verify SCHEMA_VERSION consistency
2. Check for hardcoded version strings
3. Run tests: `pytest tests/test_shared_schema_definitions.py`

## Future Enhancements

### Planned Improvements
1. **Dynamic versioning**: Auto-detect client capabilities
2. **Selective optimization**: Per-tool $ref enable/disable
3. **Schema compression**: Additional optimization techniques
4. **Metrics dashboard**: Real-time token usage monitoring

### Research Areas
1. Alternative schema optimization approaches
2. MCP protocol enhancements for better compression
3. Client-side caching of common definitions
4. Progressive schema loading strategies

## References

- [JSON Schema $ref Specification](https://json-schema.org/understanding-json-schema/structuring.html#ref)
- MCP Protocol Documentation (internal)
- Token Optimization Analysis (initial assessment)
- SharedSchemaDefinitions Source: `tools/shared/schema_definitions.py`

## Contact

For questions or issues with token optimization deployment:
- Review logs in `logs/mcp_server.log`
- Check canary test: `python test_canary_deployment.py`
- Run simulator tests: `python communication_simulator_test.py --quick`

Last Updated: 2025-09-14
Status: Ready for Production Deployment (USE_SCHEMA_REFS=true)
