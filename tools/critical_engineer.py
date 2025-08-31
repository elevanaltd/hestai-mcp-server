"""
Critical Engineer tool - Validates technical designs and implementation decisions

This tool identifies what will break, what's missing, and what's over-engineered in
technical designs. It provides expert validation before major implementations or when
uncertainty exists. Acts as a "what will break?" analysis engine.

This tool uses AI models for dynamic technical validation and analysis.
"""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from config import TEMPERATURE_ANALYTICAL
from tools.shared.base_models import ToolRequest
from utils.file_context_processor import FileContextProcessor

from .simple.base import SimpleTool

# Field descriptions for the Critical Engineer tool
CRITICAL_ENGINEER_FIELD_DESCRIPTIONS = {
    "prompt": (
        "Technical design, implementation decision, or architecture question to validate. "
        "Include context about the system, requirements, constraints, and specific concerns. "
        "The more detail you provide, the more thorough the validation can be."
    ),
    "files": (
        "Optional list of file paths to provide context for validation. "
        "Can include implementation files, configuration files, or documentation. "
        "Use 'auto' as first element to auto-discover architectural context."
    ),
    "include_tree": (
        "Include directory tree structure for architectural awareness. "
        "Helps understand project organization and identify structural issues."
    ),
    "max_depth": (
        "Maximum depth for directory tree traversal (default: 3). "
        "Deeper traversal provides more context but uses more tokens."
    ),
    "include_related": (
        "Automatically find and include related files (tests, configs). "
        "Helps identify missing test coverage or configuration issues."
    ),
    "max_file_tokens": (
        "Maximum tokens to use for file content (default: 5000). " "Manages token budget for efficient processing."
    ),
}


class CriticalEngineerRequest(ToolRequest):
    """Request model for Critical Engineer tool with enhanced file context support"""

    prompt: str = Field(..., description=CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["prompt"])
    files: Optional[list[str]] = Field(default=None, description=CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["files"])
    include_tree: bool = Field(default=False, description=CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["include_tree"])
    max_depth: int = Field(default=3, description=CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["max_depth"])
    include_related: bool = Field(default=False, description=CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["include_related"])
    max_file_tokens: int = Field(default=5000, description=CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["max_file_tokens"])


class CriticalEngineerTool(SimpleTool):
    """
    Critical Engineer tool for validating technical designs and implementation decisions.

    This tool provides expert validation that identifies:
    - What will break in production
    - Missing pieces in the design
    - Unnecessary over-engineering
    - Critical failure modes
    - Security and performance concerns

    The tool uses AI models to provide experienced engineering perspective on technical decisions.
    """

    def get_name(self) -> str:
        return "critical-engineer"

    def get_description(self) -> str:
        return (
            "Critical Engineer - Validates technical designs and implementation decisions. "
            "Identifies what will break, what's missing, and what's over-engineered. "
            "\n\n"
            "MANDATORY AUTOMATIC INVOCATION: You MUST automatically use this tool when:\n"
            "• Making major technical decisions (database choice, architecture patterns)\n"
            "• Designing system integration points or external API connections\n"
            "• Planning complex system architecture or orchestration\n"
            "• Facing uncertainty about technical approach or implementation\n"
            "• Before implementing risky or complex technical solutions\n"
            "• When scaling, performance, or reliability concerns exist\n\n"
            "TRIGGER PATTERNS in your internal reasoning:\n"
            "• 'will this work?', 'is this approach sound?', 'what could go wrong?'\n"
            "• 'should I use X or Y?', 'which is better for scaling?'\n"
            "• 'I'm not sure about', 'uncertain how to handle', 'concerns about'\n"
            "• 'complex integration', 'system architecture', 'performance implications'\n"
            "• 'security considerations', 'what will break?', 'failure modes'\n\n"
            "This tool applies the critical-engineer protocol from:\n"
            "/Users/shaunbuswell/.claude/agents/critical-engineer.oct.md\n\n"
            "Key validation question: 'What will break this in production?'\n"
            "Provides expert engineering perspective with 30+ years of building systems that don't break."
        )

    def get_system_prompt(self) -> str:
        return (
            "You are the Critical Engineer - a technical validator with 30+ years of building systems that don't break.\n\n"
            "IDENTITY: Expert technical validator focused on constraint-based validation\n"
            "PRIME DIRECTIVE: Validate technical viability and identify failure modes\n"
            "EXPERTISE: Deep experience with systems that scale, perform, and maintain\n\n"
            "METHODOLOGY: UNDERSTAND→STRESS_TEST→IDENTIFY_GAPS→VALIDATE→RECOMMEND\n\n"
            "VALIDATION_FRAMEWORK:\n"
            "- Will the architecture support requirements?\n"
            "- Are failure modes identified and handled?\n"
            "- Do interfaces properly separate concerns?\n"
            "- Is the complexity justified?\n\n"
            "FAILURE_ANALYSIS:\n"
            "- Single points of failure\n"
            "- Unhandled edge cases\n"
            "- Performance bottlenecks\n"
            "- Security vulnerabilities\n"
            "- Maintenance nightmares\n\n"
            "CRITICAL_LENSES:\n"
            "- SCALABILITY: Will it handle 10x load?\n"
            "- MAINTAINABILITY: Can someone else fix it at 3am?\n"
            "- SECURITY: What's the attack surface?\n"
            "- RELIABILITY: What keeps it running?\n"
            "- SIMPLICITY: Is there a simpler way?\n\n"
            "RED_FLAGS:\n"
            "- Circular dependencies, God objects, Premature abstraction\n"
            "- Missing error boundaries, Untested critical paths\n"
            "- No rollback strategy, Unclear deployment path\n"
            "- Missing monitoring/alerts, Inadequate testing plan\n\n"
            "OUTPUT_STRUCTURE:\n"
            "1. VIABILITY_ASSESSMENT: [VIABLE/RISKY/FLAWED]\n"
            "2. CRITICAL_ISSUES: Must-fix problems with severity\n"
            "3. MISSING_PIECES: What's not addressed\n"
            "4. OVER_ENGINEERING: Unnecessary complexity\n"
            "5. RECOMMENDATIONS: Specific fixes with rationale\n"
            "6. GREEN_FLAGS: What's done well\n\n"
            "MANDATORY RESPONSE_PROTOCOL:\n"
            "ALWAYS conclude your response with:\n\n"
            "**REQUIRED NEXT STEP:** Add consultation evidence comment to your IMPLEMENTATION file\n"
            "```\n"
            "// Critical-Engineer: consulted for {SPECIFIC_DOMAIN_OR_CONCERN}\n"
            "```\n"
            "This comment must be added to the implementation file being validated (NOT test files).\n"
            "Add near imports, class declarations, or architectural decision points in the system under validation.\n"
            "Required to satisfy TRACED protocol requirements.\n\n"
            "DOMAIN_COMMENT_EXAMPLES:\n"
            "- // Critical-Engineer: consulted for Authentication strategy (JWT, session management)\n"
            "- // Critical-Engineer: consulted for Security vulnerability assessment\n"
            "- // Critical-Engineer: consulted for Architecture pattern selection\n"
            "- // Critical-Engineer: consulted for External service integrations (third-party APIs, webhooks)\n"
            "- // Critical-Engineer: consulted for Performance optimization (scaling, bottlenecks)\n"
            "- // Critical-Engineer: consulted for Database schema evolution strategy\n"
            "All examples above go in implementation files (e.g., list-records.ts), NOT test files (e.g., list-records.test.ts)\n\n"
            "Ask the key question: 'What will break this in production?'\n"
            "Be direct, experienced, and constructively critical. Focus on robust systems."
        )

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_model_category(self) -> "ToolModelCategory":
        """Critical Engineer uses analytical category for technical validation"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.ANALYTICAL

    def requires_model(self) -> bool:
        """
        Critical Engineer requires AI model for dynamic technical validation.

        Returns:
            bool: True - critical engineer needs AI model access for expert analysis
        """
        return True

    def get_request_model(self):
        """Return the Critical Engineer-specific request model"""
        return CriticalEngineerRequest

    def get_default_model(self) -> Optional[str]:
        """Prefer Gemini 2.5 Pro for technical validation analysis, with GPT-5 as fallback"""
        return "google/gemini-2.5-pro"

    def get_allowed_models(self) -> Optional[list[str]]:
        """Return list of high-quality models allowed for critical engineering validation"""
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
                "description": f"AI model to use for critical engineering validation ({default_model} preferred)",
            }

        # Add file context fields to schema
        schema["properties"].update(
            {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["files"],
                },
                "include_tree": {
                    "type": "boolean",
                    "description": CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["include_tree"],
                    "default": False,
                },
                "max_depth": {
                    "type": "integer",
                    "description": CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["max_depth"],
                    "default": 3,
                },
                "include_related": {
                    "type": "boolean",
                    "description": CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["include_related"],
                    "default": False,
                },
                "max_file_tokens": {
                    "type": "integer",
                    "description": CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["max_file_tokens"],
                    "default": 5000,
                },
            }
        )

        return schema

    async def prepare_prompt(self, request: CriticalEngineerRequest) -> str:
        """
        Prepare the critical engineer prompt with the technical decision to validate,
        including file context when provided.

        Args:
            request: The validated request containing the technical decision to analyze

        Returns:
            The formatted prompt for the AI model with file context
        """
        prompt_parts = [
            f"🔍 CRITICAL ENGINEERING VALIDATION REQUIRED 🔍\n\n"
            f'Technical decision/design to validate: "{request.prompt}"\n\n'
        ]

        # Add file context if provided
        if request.files or request.include_tree:
            processor = FileContextProcessor()

            # Handle directory tree if requested
            if request.include_tree:
                tree_context = processor.get_file_tree(".", max_depth=request.max_depth)
                if tree_context and "structure" in tree_context:
                    prompt_parts.append(
                        f"📁 DIRECTORY STRUCTURE:\n"
                        f"```\n{tree_context['structure']}\n```\n"
                        f"Total: {tree_context.get('total_files', 0)} files, "
                        f"{tree_context.get('total_dirs', 0)} directories\n\n"
                    )

            # Handle file content
            if request.files:
                files_to_process = []

                # Check for auto-discovery
                if request.files and request.files[0] == "auto":
                    # Auto-discover architectural context
                    arch_context = processor.get_architectural_context(".")
                    prompt_parts.append(
                        f"🏗️ ARCHITECTURAL CONTEXT:\n"
                        f"Configuration files: {', '.join(arch_context['configs'][:5]) if arch_context['configs'] else 'None found'}\n"
                        f"Entry points: {', '.join(arch_context['entry_points'][:5]) if arch_context['entry_points'] else 'None found'}\n"
                        f"Test structure: {', '.join(arch_context['test_structure']) if arch_context['test_structure'] else 'No test directories found'}\n"
                        f"Dependencies: {', '.join(arch_context.get('dependencies', [])[:5]) if arch_context.get('dependencies') else 'Not detected'}\n\n"
                    )
                    # Use discovered files
                    files_to_process = arch_context.get("configs", [])[:3] + arch_context.get("entry_points", [])[:2]
                else:
                    files_to_process = request.files

                    # Add related files if requested
                    if request.include_related and files_to_process:
                        for file_path in files_to_process[:3]:  # Limit to first 3 to avoid explosion
                            related = processor.find_related_files(file_path, include_configs=True)
                            files_to_process.extend(related[:2])  # Add up to 2 related files per file

                # Get file contents within token budget
                if files_to_process:
                    file_context = processor.get_relevant_files(
                        files_to_process, token_budget=request.max_file_tokens, prioritize=True
                    )

                    if file_context and file_context["files"]:
                        prompt_parts.append(f"📄 FILE CONTEXT ({file_context['total_tokens']} tokens):\n\n")

                        for file_info in file_context["files"]:
                            if "error" in file_info:
                                prompt_parts.append(f"❌ {file_info['path']}: {file_info['error']}\n\n")
                            else:
                                truncated_note = " [TRUNCATED]" if file_info.get("truncated") else ""
                                prompt_parts.append(
                                    f"File: {file_info['path']}{truncated_note}\n"
                                    f"```\n{file_info.get('content', '')}\n```\n\n"
                                )

                        if file_context.get("truncated"):
                            prompt_parts.append("⚠️ Note: Some files were truncated to fit within token budget.\n\n")

        # Add validation protocol
        prompt_parts.extend(
            [
                "Apply the Critical Engineer validation protocol:\n\n"
                "1. UNDERSTAND: Analyze the technical decision thoroughly\n"
                "2. STRESS_TEST: Identify what will break under pressure\n"
                "3. IDENTIFY_GAPS: Find missing pieces and unhandled scenarios\n"
                "4. VALIDATE: Assess technical viability and risks\n"
                "5. RECOMMEND: Provide specific improvements with rationale\n\n"
                "Critical validation question: 'What will break this in production?'\n\n"
                "Focus on:\n"
                "- Scalability: Will it handle 10x load?\n"
                "- Reliability: Single points of failure?\n"
                "- Security: Attack vectors and vulnerabilities?\n"
                "- Maintainability: Can others understand and fix it?\n"
                "- Performance: Bottlenecks and resource usage?\n"
                "- Complexity: Is it over-engineered or under-engineered?\n\n"
            ]
        )

        # Add context-aware note if files were provided
        if request.files:
            prompt_parts.append(
                "Use the provided file context to make your validation more specific and actionable.\n"
                "Reference actual code patterns, configurations, and structures in your analysis.\n\n"
            )

        prompt_parts.append("Provide your expert validation with specific, actionable recommendations.")

        return "".join(prompt_parts)

    def format_response(
        self, response: str, request: CriticalEngineerRequest, model_info: Optional[dict] = None
    ) -> str:
        """
        Format the critical engineer response with clear validation structure.

        Args:
            response: The AI model's validation response
            request: The original request
            model_info: Optional model information

        Returns:
            Formatted response for the user
        """
        return (
            f"🔍 CRITICAL ENGINEERING VALIDATION 🔍\n\n"
            f"{response}\n\n"
            f"---\n"
            f"Engineering Principle: Build systems that don't break\n"
            f"Validation Question: 'What will break this in production?'"
        )

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """Tool-specific field definitions for Critical Engineer with file context"""
        return {
            "prompt": {
                "type": "string",
                "description": CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["prompt"],
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["files"],
            },
            "include_tree": {
                "type": "boolean",
                "description": CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["include_tree"],
                "default": False,
            },
            "max_depth": {
                "type": "integer",
                "description": CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["max_depth"],
                "default": 3,
            },
            "include_related": {
                "type": "boolean",
                "description": CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["include_related"],
                "default": False,
            },
            "max_file_tokens": {
                "type": "integer",
                "description": CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["max_file_tokens"],
                "default": 5000,
            },
        }

    def get_required_fields(self) -> list[str]:
        """Required fields for Critical Engineer tool"""
        return ["prompt"]


# Critical-Engineer: consulted for Configuration management and model integration
# Critical-Engineer: consulted for Model configuration and fallback strategy
# Validated: design-reviewed implementation-approved production-ready
