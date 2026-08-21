import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.opportunity_config import get_opportunity_intelligence_settings
from app.schemas.opportunity import ExtractedOpportunity


class RequirementExtractionError(RuntimeError):
    pass


SYSTEM_INSTRUCTIONS = """
You extract procurement, tender, TOR, RFP, staffing and job requirements for Capability Flow.
Never invent qualifications that are not supported by the source.
Separate required team roles from team-level constraints.
Preserve mandatory vs preferred wording.
Normalize common skill, certification and degree names while keeping a human-readable label.

For a role requirement use requirement_type values only from:
skill, education, certification, experience, project_experience, sector, geography, language,
availability, client_experience, document, custom.

importance must be mandatory, preferred, or informational.
For education, set minimum_degree_level when stated.
For experience/project experience, set minimum_years or minimum_count when stated.
For one-of alternatives, put normalized alternatives in values and operator='one_of'.
For normal text matches use operator='match'.
Use weight 3 for mandatory, 1 for preferred, and 0.25 for informational unless the source
clearly implies otherwise.
Include short source_excerpt strings supporting each extracted requirement.

Use the extract_opportunity tool exactly once with the complete structured result.
""".strip()


class ClaudeRequirementExtractor:
    def __init__(self) -> None:
        self.settings = get_opportunity_intelligence_settings()

        if not self.settings.anthropic_api_key:
            raise RequirementExtractionError(
                "ANTHROPIC_API_KEY is required for automatic requirement extraction"
            )

    async def extract(self, source_text: str) -> ExtractedOpportunity:
        schema = ExtractedOpportunity.model_json_schema()

        payload: dict[str, Any] = {
            "model": self.settings.anthropic_model,
            "max_tokens": self.settings.anthropic_max_tokens,
            "temperature": 0,
            "system": SYSTEM_INSTRUCTIONS,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Analyze the following client opportunity. "
                        "Use the extract_opportunity tool with the complete result.\n\n"
                        f"SOURCE:\n{source_text}"
                    ),
                }
            ],
            "tools": [
                {
                    "name": "extract_opportunity",
                    "description": (
                        "Return the normalized opportunity, roles, requirements, "
                        "and team-level constraints extracted from the client source."
                    ),
                    "input_schema": schema,
                }
            ],
            "tool_choice": {
                "type": "tool",
                "name": "extract_opportunity",
            },
        }

        api_key = self.settings.anthropic_api_key
        if not api_key:
            raise RequirementExtractionError(
                "ANTHROPIC_API_KEY is required for automatic requirement extraction"
            )

        headers: dict[str, str] = {
            "x-api-key": api_key,
            "anthropic-version": self.settings.anthropic_version,
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.settings.anthropic_api_url,
                    headers=headers,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise RequirementExtractionError(f"Claude API request failed: {exc}") from exc

        if response.is_error:
            detail = self._api_error_detail(response)
            raise RequirementExtractionError(
                f"Claude API returned HTTP {response.status_code}: {detail}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise RequirementExtractionError(
                "Claude API returned an invalid JSON response"
            ) from exc

        tool_input = self._extract_tool_input(body)

        try:
            return ExtractedOpportunity.model_validate(tool_input)
        except (ValidationError, ValueError, TypeError) as exc:
            raise RequirementExtractionError(
                f"Claude extraction returned invalid structured data: {exc}"
            ) from exc

    @staticmethod
    def _extract_tool_input(body: dict[str, Any]) -> dict[str, Any]:
        content = body.get("content")

        if not isinstance(content, list):
            raise RequirementExtractionError("Claude API response did not contain content blocks")

        for block in content:
            if not isinstance(block, dict):
                continue

            if block.get("type") == "tool_use" and block.get("name") == "extract_opportunity":
                tool_input = block.get("input")

                if isinstance(tool_input, dict):
                    return tool_input

        raise RequirementExtractionError(
            "Claude did not return the required extract_opportunity tool result"
        )

    @staticmethod
    def _api_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:500] or "Unknown Anthropic API error"

        error = payload.get("error")

        if isinstance(error, dict):
            message = error.get("message")

            if isinstance(message, str):
                return message

        return json.dumps(payload)[:500]
