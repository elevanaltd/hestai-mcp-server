"""
Test canary deployment to verify MCP client $ref support.
"""

import asyncio
import json
import logging

from server import TOOLS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_canary_tool():
    """Test the canary tool is available and schema is correct."""

    # Check canary tool is registered
    canary_tool = TOOLS.get("canary_ref_test")
    if not canary_tool:
        logger.error("Canary tool not found in TOOLS registry!")
        return False

    logger.info("✓ Canary tool found in registry")

    # Check schema has $ref
    schema = canary_tool.get_input_schema()
    schema_json = json.dumps(schema, indent=2)

    logger.info("Canary tool schema:")
    print(schema_json)

    # Verify $ref structure
    if "$defs" not in schema:
        logger.error("Missing $defs in schema")
        return False

    if "v1" not in schema["$defs"]:
        logger.error("Missing v1 in $defs")
        return False

    if "confidence" not in schema["properties"]:
        logger.error("Missing confidence property")
        return False

    confidence_prop = schema["properties"]["confidence"]
    if "$ref" not in confidence_prop:
        logger.error("Missing $ref in confidence property")
        return False

    if confidence_prop["$ref"] != "#/$defs/v1/confidence_enum":
        logger.error(f"Wrong $ref path: {confidence_prop['$ref']}")
        return False

    logger.info("✓ Schema has correct $ref structure")

    # Test execution
    result = await canary_tool.execute(test_message="Testing MCP $ref support", confidence="high")

    logger.info(f"✓ Canary tool executed successfully: {result}")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_canary_tool())
    if success:
        print("\n🎯 CANARY TEST SUCCESSFUL - MCP client should support $ref")
        print("✓ Ready to enable USE_SCHEMA_REFS=true for production")
    else:
        print("\n❌ CANARY TEST FAILED - Check implementation")
