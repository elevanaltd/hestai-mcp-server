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

from .simple.base import SimpleTool

# Field descriptions for the Critical Engineer tool
CRITICAL_ENGINEER_FIELD_DESCRIPTIONS = {
    "prompt": (
        "Technical design, implementation decision, or architecture question to validate. "
        "Include context about the system, requirements, constraints, and specific concerns. "
        "The more detail you provide, the more thorough the validation can be."
    ),
}


class CriticalEngineerRequest(ToolRequest):
    """Request model for Critical Engineer tool"""

    prompt: str = Field(..., description=CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["prompt"])


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
        return "gemini-2.5-pro"
    
    def get_allowed_models(self) -> Optional[list[str]]:
        """Return list of high-quality models allowed for critical engineering validation"""
        return ["google/gemini-2.5-pro", "openai/gpt-5"]

    def get_input_schema(self) -> dict[str, Any]:
        """
        Override input schema to only allow high-quality models for critical engineering validation.
        Restricted to gemini-2.5-pro (preferred) and gpt-5 (fallback).
        """
        # Get the base schema from SimpleTool
        schema = super().get_input_schema()
        
        # Restrict model options to high-quality models only
        if "model" in schema.get("properties", {}):
            schema["properties"]["model"] = {
                "type": "string",
                "enum": ["google/gemini-2.5-pro", "openai/gpt-5"],
                "default": "google/gemini-2.5-pro",
                "description": "AI model to use for critical engineering validation (gemini-2.5-pro preferred, gpt-5 fallback)"
            }
            
        return schema

    async def prepare_prompt(self, request: CriticalEngineerRequest) -> str:
        """
        Prepare the critical engineer prompt with the technical decision to validate.
        
        Args:
            request: The validated request containing the technical decision to analyze
            
        Returns:
            The formatted prompt for the AI model
        """
        return (
            f"🔍 CRITICAL ENGINEERING VALIDATION REQUIRED 🔍\n\n"
            f"Technical decision/design to validate: \"{request.prompt}\"\n\n"
            f"Apply the Critical Engineer validation protocol:\n\n"
            f"1. UNDERSTAND: Analyze the technical decision thoroughly\n"
            f"2. STRESS_TEST: Identify what will break under pressure\n"
            f"3. IDENTIFY_GAPS: Find missing pieces and unhandled scenarios\n"
            f"4. VALIDATE: Assess technical viability and risks\n"
            f"5. RECOMMEND: Provide specific improvements with rationale\n\n"
            f"Critical validation question: 'What will break this in production?'\n\n"
            f"Focus on:\n"
            f"- Scalability: Will it handle 10x load?\n"
            f"- Reliability: Single points of failure?\n"
            f"- Security: Attack vectors and vulnerabilities?\n"
            f"- Maintainability: Can others understand and fix it?\n"
            f"- Performance: Bottlenecks and resource usage?\n"
            f"- Complexity: Is it over-engineered or under-engineered?\n\n"
            f"Provide your expert validation with specific, actionable recommendations."
        )

    def format_response(self, response: str, request: CriticalEngineerRequest, model_info: Optional[dict] = None) -> str:
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
        """Tool-specific field definitions for Critical Engineer"""
        return {
            "prompt": {
                "type": "string",
                "description": CRITICAL_ENGINEER_FIELD_DESCRIPTIONS["prompt"],
            },
        }

    def get_required_fields(self) -> list[str]:
        """Required fields for Critical Engineer tool"""
        return ["prompt"]