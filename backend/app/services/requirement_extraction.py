import json

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.opportunity_config import get_opportunity_intelligence_settings
from app.schemas.opportunity import ExtractedOpportunity


class RequirementExtractionError(RuntimeError):
    pass


SYSTEM_INSTRUCTIONS = """
You extract procurement, tender, TOR, RFP, staffing and consulting requirements for
Capability Flow.

Return only information supported by the source. Never invent qualifications, dates,
clients, reference numbers, staffing roles, certifications or experience requirements.

Identify both explicitly named roles and unmistakably requested individual roles. For
example, if the source clearly says it is recruiting one consultant to conduct an
evaluation, create an appropriate consultant/evaluator role. Do not create a role merely
because a document discusses staff generally.

Separate role-level requirements from team-level constraints. Preserve mandatory versus
preferred wording. Normalize common skill, certification and degree names while keeping
a human-readable label.

For a role requirement, requirement_type must be one of:
skill, education, certification, experience, project_experience, sector, geography,
language, availability, client_experience, document, custom.

importance must be mandatory, preferred, or informational.
For education, set minimum_degree_level when stated.
For experience and project experience, set minimum_years or minimum_count when stated.
For one-of alternatives, put normalized alternatives in values and use operator='one_of'.
For normal text matches use operator='match'.
Use weight 3 for mandatory, 1 for preferred, and 0.25 for informational unless the source
clearly supports a different relative importance.
Include a short source_excerpt supporting each extracted requirement.

Metadata rules:
- title is the opportunity or assignment title, not an email salutation or sender name.
- client_name is the procuring/recruiting organization when clearly identified.
- reference_number must be an actual tender/RFP/reference identifier. Never return words
  such as 'reference', 'ref', 'number', 'tender', or fragments of those words.
- deadline_at must only be returned when a submission/application deadline is stated.

If no assessable human role can be identified, return roles as an empty list.
""".strip()


class GeminiRequirementExtractor:
    def __init__(self) -> None:
        self.app_settings = get_settings()
        self.opportunity_settings = get_opportunity_intelligence_settings()

        if not self.app_settings.gemini_api_key:
            raise RequirementExtractionError(
                "GEMINI_API_KEY is required for automatic opportunity analysis"
            )

    @property
    def model_name(self) -> str:
        return self.app_settings.ai_model

    async def extract(self, source_text: str) -> ExtractedOpportunity:
        source_text = source_text[: self.opportunity_settings.opportunity_max_source_characters]
        schema = ExtractedOpportunity.model_json_schema()

        request_content = types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=(
                        "Analyze the client opportunity below and return the complete "
                        "structured result.\n\nSOURCE:\n"
                        f"{source_text}"
                    )
                )
            ],
        )

        try:
            async with genai.Client(api_key=self.app_settings.gemini_api_key).aio as client:
                response = await client.models.generate_content(
                    model=self.model_name,
                    contents=request_content,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        response_mime_type="application/json",
                        response_json_schema=schema,
                        max_output_tokens=8192,
                        temperature=0.1,
                    ),
                )
        except Exception as exc:
            raise RequirementExtractionError(f"Gemini analysis failed: {exc}") from exc

        payload = (response.text or "").strip()
        if not payload:
            raise RequirementExtractionError("Gemini returned an empty opportunity analysis")

        try:
            data = json.loads(payload)
            return ExtractedOpportunity.model_validate(data)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise RequirementExtractionError(
                "Gemini returned an opportunity analysis that could not be validated"
            ) from exc
