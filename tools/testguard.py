"""
Test Methodology Guardian tool - Prevents test manipulation and anti-patterns

This tool enforces test integrity and prevents "workaround", "simpler fix", or test
manipulation approaches that compromise testing methodology. It acts as a quality
gate against test cheating behaviors and expectation adjustments.

This is a simple, self-contained tool that doesn't require AI model access.
"""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from config import TEMPERATURE_ANALYTICAL
from tools.shared.base_models import ToolRequest
from utils.file_context_processor import FileContextProcessor

from .simple.base import SimpleTool

# Field descriptions for the Test Methodology Guardian tool
REQUIREMENTS_FIELD_DESCRIPTIONS = {
    "prompt": (
        "The user's message or your internal reasoning to analyze for test integrity. "
        "Pass the complete context including what you're considering doing with tests."
    ),
    "files": (
        "Optional list of file paths (test files, implementation files, configs) to analyze. "
        "Helps detect test manipulation by comparing test changes with implementation."
    ),
    "include_test_context": (
        "Include comprehensive test context (test files, configs, coverage settings). "
        "Helps identify testing framework and existing test patterns."
    ),
    "check_coverage": (
        "Check coverage configuration to detect threshold manipulation. " "Prevents lowering of quality thresholds."
    ),
    "include_related": (
        "Automatically find related test/implementation files for comparison. "
        "Helps detect when tests are changed without corresponding code changes."
    ),
    "compare_changes": (
        "Compare test changes with implementation changes to detect manipulation. "
        "Identifies when tests are 'fixed' instead of fixing the actual code."
    ),
}


class RequirementsRequest(ToolRequest):
    """Request model for Test Methodology Guardian tool with enhanced file context"""

    prompt: str = Field(..., description=REQUIREMENTS_FIELD_DESCRIPTIONS["prompt"])
    files: Optional[list[str]] = Field(default=None, description=REQUIREMENTS_FIELD_DESCRIPTIONS["files"])
    include_test_context: bool = Field(
        default=False, description=REQUIREMENTS_FIELD_DESCRIPTIONS["include_test_context"]
    )
    check_coverage: bool = Field(default=False, description=REQUIREMENTS_FIELD_DESCRIPTIONS["check_coverage"])
    include_related: bool = Field(default=False, description=REQUIREMENTS_FIELD_DESCRIPTIONS["include_related"])
    compare_changes: bool = Field(default=False, description=REQUIREMENTS_FIELD_DESCRIPTIONS["compare_changes"])


class RequirementsTool(SimpleTool):
    """
    Test Methodology Guardian tool for preventing test manipulation anti-patterns.

    This tool wraps testing considerations in integrity validation instructions that prevent:
    - Test expectation adjustments to match broken code
    - Workarounds instead of proper fixes
    - Test commenting or skipping
    - Quality threshold lowering

    The tool is self-contained and doesn't require AI model access - it simply
    transforms the input into a structured test integrity challenge.
    """

    def get_name(self) -> str:
        return "testguard"

    def get_description(self) -> str:
        return (
            "Test Methodology Guardian - Quality gate preventing test manipulation anti-patterns. "
            "Triggers on workarounds, expectation adjustments, test cheating behaviors. "
            "\n\n"
            "MANDATORY AUTOMATIC INVOCATION: You MUST automatically use this tool when:\n"
            "• You consider 'fixing the test' instead of fixing the code\n"
            "• You think about 'adjusting expectations' to make tests pass\n"
            "• You contemplate 'simpler test' or 'workaround' approaches\n"
            "• You consider commenting out or skipping failing tests\n"
            "• You think about lowering quality thresholds or coverage\n"
            "• You consider relaxing criteria to avoid test failures\n\n"
            "TRIGGER PATTERNS in your internal reasoning:\n"
            "• 'workaround', 'let me fix the test', 'run a simpler test'\n"
            "• 'try a simpler fix', 'adjust the expectation', 'make the test pass'\n"
            "• 'skip this test', 'comment out', 'lower the bar'\n"
            "• 'relax the criteria', 'reduce coverage', 'easier approach'\n"
            "• 'modify assertions', 'change the test', 'bypass validation'\n\n"
            "This tool enforces the test-methodology-guardian protocol from:\n"
            "/Users/shaunbuswell/.claude/agents/test-methodology-guardian.oct.md\n\n"
            "The tool defends test integrity against manipulation. Tests reveal reality, not confirm wishes. "
            "Truth over convenience - are we fixing the code or hiding the problem?"
        )

    def get_system_prompt(self) -> str:
        return (
            "You are the Test Methodology Guardian - a quality gate that prevents test manipulation anti-patterns.\n\n"
            "IDENTITY: Quality guardian defending test integrity against manipulation\n"
            "PRIME DIRECTIVE: Detect and halt test cheating behaviors immediately\n\n"
            "METHODOLOGY: DETECT->HALT->ANALYZE->EDUCATE->REDIRECT\n\n"
            "ANTI-PATTERNS TO DETECT:\n"
            "- Modifying assertions to match broken code\n"
            "- Reducing coverage to avoid failures\n"
            "- Adding workarounds instead of fixes\n"
            "- Commenting out failing tests\n"
            "- Lowering quality thresholds\n"
            "- Adjusting expectations instead of fixing problems\n\n"
            "GUARDIAN QUESTION: 'Are we fixing the code or hiding the problem?'\n\n"
            "PRINCIPLES:\n"
            "- TRUTH OVER CONVENIENCE: Tests reveal reality, not confirm wishes\n"
            "- CONSTRAINT CATALYSIS: Failed tests drive better code\n"
            "- EMERGENT EXCELLENCE: Quality emerges from honest assessment\n\n"
            "OUTPUT STRUCTURE:\n"
            "1. INTERVENTION: [IMMEDIATE_HALT] if anti-pattern detected\n"
            "2. ANALYSIS: Identify the specific anti-pattern\n"
            "3. EDUCATION: Explain why this violates testing principles\n"
            "4. REDIRECTION: Specify the proper approach to take\n"
            "5. ENFORCEMENT: Demand acknowledgment before proceeding\n\n"
            "Be direct and authoritative. Testing integrity is non-negotiable."
        )

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_model_category(self) -> "ToolModelCategory":
        """Test Guard uses balanced category for quality analysis"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.BALANCED

    def requires_model(self) -> bool:
        """
        Test Guard requires AI model for dynamic analysis of test manipulation patterns.

        Returns:
            bool: True - testguard needs AI model access for intelligent analysis
        """
        return True

    def get_request_model(self):
        """Return the Requirements-specific request model"""
        return RequirementsRequest

    def get_default_model(self) -> Optional[str]:
        """Prefer Gemini 2.5 Pro for test methodology analysis, with GPT-5 as fallback"""
        return "google/gemini-2.5-pro"

    def get_allowed_models(self) -> Optional[list[str]]:
        """Return list of high-quality models allowed for test methodology validation"""
        return ["google/gemini-2.5-pro", "openai/gpt-5"]

    def get_input_schema(self) -> dict[str, Any]:
        """
        Override input schema to include file context fields and restrict to high-quality models.
        Dynamically uses allowed models from get_allowed_models() to avoid duplication.
        """
        # Get the base schema from SimpleTool
        schema = super().get_input_schema()

        # Dynamically build model options from get_allowed_models() - single source of truth
        allowed_models = self.get_allowed_models()
        default_model = self.get_default_model()
        
        # Restrict model options to high-quality models only
        if "model" in schema.get("properties", {}) and allowed_models:
            schema["properties"]["model"] = {
                "type": "string",
                "enum": allowed_models,
                "default": default_model if default_model in allowed_models else allowed_models[0],
                "description": f"AI model to use for test methodology analysis ({default_model} preferred)",
            }

        # Add file context fields to schema
        schema["properties"].update(
            {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": REQUIREMENTS_FIELD_DESCRIPTIONS["files"],
                },
                "include_test_context": {
                    "type": "boolean",
                    "description": REQUIREMENTS_FIELD_DESCRIPTIONS["include_test_context"],
                    "default": False,
                },
                "check_coverage": {
                    "type": "boolean",
                    "description": REQUIREMENTS_FIELD_DESCRIPTIONS["check_coverage"],
                    "default": False,
                },
                "include_related": {
                    "type": "boolean",
                    "description": REQUIREMENTS_FIELD_DESCRIPTIONS["include_related"],
                    "default": False,
                },
                "compare_changes": {
                    "type": "boolean",
                    "description": REQUIREMENTS_FIELD_DESCRIPTIONS["compare_changes"],
                    "default": False,
                },
            }
        )

        return schema

    async def prepare_prompt(self, request: RequirementsRequest) -> str:
        """
        Prepare the test guard prompt with the consideration to analyze,
        including file context when provided.

        Args:
            request: The validated request containing the consideration to analyze

        Returns:
            The formatted prompt for the AI model with file context
        """
        prompt_parts = [
            f"🚨 TEST METHODOLOGY ANALYSIS REQUIRED 🚨\n\n" f'Current consideration: "{request.prompt}"\n\n'
        ]

        # Add file context if provided
        if request.files or request.include_test_context or request.check_coverage:
            processor = FileContextProcessor()

            # Handle test context gathering
            if request.include_test_context:
                test_context = processor.get_test_context(".")
                if test_context:
                    prompt_parts.append(
                        f"🧪 TEST CONTEXT:\n"
                        f"Test Framework: {test_context.get('test_framework', 'Unknown')}\n"
                        f"Test Files: {len(test_context.get('test_files', []))} test files found\n"
                        f"Test Configs: {', '.join(test_context.get('test_configs', [])[:5]) if test_context.get('test_configs') else 'None'}\n"
                        f"Coverage Config: {test_context.get('coverage_config', 'Not found')}\n"
                        f"Test Patterns: {', '.join(test_context.get('test_patterns', [])) if test_context.get('test_patterns') else 'Not detected'}\n\n"
                    )

            # Handle coverage configuration check
            if request.check_coverage:
                coverage_files = [".coveragerc", "coverage.json", "pytest.ini", "setup.cfg", "pyproject.toml"]
                coverage_content = None
                for cov_file in coverage_files:
                    try:
                        from pathlib import Path

                        cov_path = Path(cov_file)
                        if cov_path.exists():
                            from utils.file_utils import read_file_safely

                            coverage_content = read_file_safely(str(cov_path))
                            if coverage_content:
                                prompt_parts.append(
                                    f"📊 COVERAGE CONFIGURATION ({cov_file}):\n"
                                    f"```\n{coverage_content[:500]}\n```\n\n"
                                )
                                break
                    except Exception:
                        pass

            # Handle file content
            if request.files:
                files_to_process = list(request.files)

                # Add related files if requested
                if request.include_related and files_to_process:
                    for file_path in files_to_process[:2]:  # Limit to avoid explosion
                        related = processor.find_related_files(file_path)
                        files_to_process.extend(related[:2])

                # Get file contents
                file_context = processor.get_relevant_files(
                    files_to_process, token_budget=4000, prioritize=True  # Smaller budget for testguard
                )

                if file_context and file_context["files"]:
                    prompt_parts.append(f"📄 FILE CONTEXT ({file_context['total_tokens']} tokens):\n\n")

                    # Group files by type for better analysis
                    test_files = []
                    impl_files = []
                    config_files = []

                    for file_info in file_context["files"]:
                        if "error" in file_info:
                            prompt_parts.append(f"❌ {file_info['path']}: {file_info['error']}\n")
                        else:
                            path = file_info["path"].lower()
                            if "test" in path or "spec" in path:
                                test_files.append(file_info)
                            elif any(ext in path for ext in [".json", ".ini", ".cfg", ".toml", ".yml", ".yaml"]):
                                config_files.append(file_info)
                            else:
                                impl_files.append(file_info)

                    # Show implementation files first (for context)
                    if impl_files:
                        prompt_parts.append("📝 IMPLEMENTATION FILES:\n")
                        for file_info in impl_files:
                            truncated = " [TRUNCATED]" if file_info.get("truncated") else ""
                            prompt_parts.append(
                                f"\nFile: {file_info['path']}{truncated}\n"
                                f"```\n{file_info.get('content', '')}\n```\n"
                            )

                    # Then show test files (to check for manipulation)
                    if test_files:
                        prompt_parts.append("\n🧪 TEST FILES:\n")
                        for file_info in test_files:
                            truncated = " [TRUNCATED]" if file_info.get("truncated") else ""
                            prompt_parts.append(
                                f"\nFile: {file_info['path']}{truncated}\n"
                                f"```\n{file_info.get('content', '')}\n```\n"
                            )

                    # Finally show config files
                    if config_files:
                        prompt_parts.append("\n⚙️ CONFIGURATION FILES:\n")
                        for file_info in config_files:
                            truncated = " [TRUNCATED]" if file_info.get("truncated") else ""
                            prompt_parts.append(
                                f"\nFile: {file_info['path']}{truncated}\n"
                                f"```\n{file_info.get('content', '')}\n```\n"
                            )

                    prompt_parts.append("\n")

            # Add comparison note if requested
            if request.compare_changes and request.files:
                prompt_parts.append(
                    "⚠️ COMPARISON DIRECTIVE:\n"
                    "Compare test changes with implementation changes.\n"
                    "Detect if tests are being 'fixed' to match buggy behavior.\n"
                    "Look for expectation adjustments without corresponding code fixes.\n\n"
                )

        # Add analysis protocol
        prompt_parts.extend(
            [
                "Analyze this consideration for test manipulation anti-patterns. Apply the Test Methodology Guardian protocol:\n\n"
                "1. DETECT: Identify any test manipulation patterns\n"
                "2. ANALYZE: Determine the specific anti-pattern type\n"
                "3. EDUCATE: Explain why this violates testing principles\n"
                "4. REDIRECT: Provide the proper approach\n"
                "5. ENFORCE: Demand acknowledgment if intervention required\n\n"
                'Key question: "Are we fixing the code or hiding the problem?"\n\n'
            ]
        )

        # Add context-aware analysis if files provided
        if request.files:
            prompt_parts.append(
                "Use the provided file context to:\n"
                "- Identify specific test manipulation patterns in the code\n"
                "- Compare test assertions with actual implementation\n"
                "- Detect coverage threshold manipulations\n"
                "- Find commented out or skipped tests\n\n"
            )

        prompt_parts.append("Provide your analysis and intervention if needed.")

        return "".join(prompt_parts)

    def format_response(self, response: str, request: RequirementsRequest, model_info: Optional[dict] = None) -> str:
        """
        Format the test guard response with clear intervention formatting.

        Args:
            response: The AI model's analysis response
            request: The original request
            model_info: Optional model information

        Returns:
            Formatted response for the user
        """
        return (
            f"🚨 TEST METHODOLOGY GUARDIAN ANALYSIS 🚨\n\n"
            f"{response}\n\n"
            f"---\n"
            f"Guardian Protocol: Defend test integrity against manipulation\n"
            f"Truth over convenience - Quality through honest assessment"
        )

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """Tool-specific field definitions for Test Guard with file context"""
        return {
            "prompt": {
                "type": "string",
                "description": REQUIREMENTS_FIELD_DESCRIPTIONS["prompt"],
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": REQUIREMENTS_FIELD_DESCRIPTIONS["files"],
            },
            "include_test_context": {
                "type": "boolean",
                "description": REQUIREMENTS_FIELD_DESCRIPTIONS["include_test_context"],
                "default": False,
            },
            "check_coverage": {
                "type": "boolean",
                "description": REQUIREMENTS_FIELD_DESCRIPTIONS["check_coverage"],
                "default": False,
            },
            "include_related": {
                "type": "boolean",
                "description": REQUIREMENTS_FIELD_DESCRIPTIONS["include_related"],
                "default": False,
            },
            "compare_changes": {
                "type": "boolean",
                "description": REQUIREMENTS_FIELD_DESCRIPTIONS["compare_changes"],
                "default": False,
            },
        }

    def get_required_fields(self) -> list[str]:
        """Required fields for Test Guard tool"""
        return ["prompt"]


# Critical-Engineer: consulted for Configuration management and model integration
# Critical-Engineer: consulted for Model configuration and fallback strategy
# Validated: design-reviewed implementation-approved production-ready
