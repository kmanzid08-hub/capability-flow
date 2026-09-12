import json
import re
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.opportunity_config import get_opportunity_intelligence_settings
from app.core.partial_dates import normalize_partial_date
from app.schemas.opportunity import ExtractedOpportunity
from app.services.ai_fallback import AllAIProvidersUnavailable, FallbackAI


def _normalize_opportunity_dates(payload: dict[str, Any]) -> dict[str, Any]:
    date_fields = (
        "deadline_at",
        "start_date",
        "end_date",
        "contract_start_date",
        "contract_end_date",
    )

    cleaned = dict(payload)

    for field in date_fields:
        if cleaned.get(field):
            try:
                cleaned[field] = normalize_partial_date(cleaned[field])
            except Exception:
                cleaned[field] = None

    return cleaned


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

Precision rules for matching:
- Extract the exact discipline, subject area, certification, sector, geography, project type,
  client type and experience area requested. Do not reduce a specific requirement to a broad
  category merely to create more matches.
- For education, separate degree level from discipline. Example: "Master's in Agriculture or
  Chemistry" means minimum_degree_level='master' and discipline alternatives such as
  agriculture and chemistry. A Master's in Economics or Finance is not an education match.
- Split explicit alternatives into values and use operator='one_of'. Preserve phrases such as
  "or related field", "equivalent", or "relevant discipline" in the label/notes, but do not
  invent related disciplines that the source does not support.
- For experience, do not extract only a number of years when the source requires years in a
  particular sector, technical area, client category, or type of assignment. Preserve that
  subject as normalized_value/values so matching evaluates relevant years rather than total
  career length.
- For project experience, capture the actual project domain and minimum project count/duration.
- For certifications, preserve the specific credential or explicit alternatives. Do not treat
  unrelated professional certificates as equivalent.
- Precision is more important than forcing a candidate to fit. It is valid for no candidate to
  satisfy a mandatory requirement. At the same time, preserve legitimate synonyms, acronyms,
  reordered wording and clearly stated alternatives so genuinely qualified people are not lost.

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
        self.fallback_ai = FallbackAI(self.app_settings)

        if not self.app_settings.gemini_api_key and not self.fallback_ai.configured:
            raise RequirementExtractionError(
                "Configure GEMINI_API_KEY, GROQ_API_KEY, or OPENROUTER_API_KEY for analysis"
            )

    @property
    def model_name(self) -> str:
        if self.app_settings.gemini_api_key:
            return self.app_settings.ai_model
        if self.app_settings.groq_api_key:
            return f"groq:{self.app_settings.groq_model}"
        return f"openrouter:{self.app_settings.openrouter_model}"

    async def extract(self, source_text: str) -> ExtractedOpportunity:
        source_text = source_text[: self.opportunity_settings.opportunity_max_source_characters]
        chunks = self._chunk_source(source_text)
        results: list[ExtractedOpportunity] = []

        for index, chunk in enumerate(chunks, start=1):
            results.append(
                await self._extract_one(
                    chunk,
                    chunk_index=index,
                    chunk_count=len(chunks),
                )
            )

        return self._merge_results(results)

    async def _extract_one(
        self,
        source_text: str,
        *,
        chunk_index: int,
        chunk_count: int,
    ) -> ExtractedOpportunity:
        schema = ExtractedOpportunity.model_json_schema()
        chunk_note = (
            f" This is source chunk {chunk_index} of {chunk_count}. "
            "Extract every supported requirement in this chunk; do not assume omitted "
            "sections are absent from the full source."
            if chunk_count > 1
            else ""
        )
        user_prompt = (
            "Analyze the client opportunity below and return the complete structured result."
            f"{chunk_note}\n\nSOURCE:\n{source_text}"
        )
        gemini_error: Exception | None = None

        if self.app_settings.gemini_api_key:
            request_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_prompt)],
            )
            try:
                async with genai.Client(api_key=self.app_settings.gemini_api_key).aio as client:
                    response = await client.models.generate_content(
                        model=self.app_settings.ai_model,
                        contents=request_content,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTIONS,
                            response_mime_type="application/json",
                            response_json_schema=schema,
                            max_output_tokens=8192,
                            temperature=0.1,
                        ),
                    )
                payload = (response.text or "").strip()
                if not payload:
                    raise ValueError("Gemini returned an empty opportunity analysis")
                return ExtractedOpportunity.model_validate(json.loads(payload))
            except Exception as exc:
                gemini_error = exc

        if self.fallback_ai.configured:
            try:
                data, _provider = await self.fallback_ai.generate_json(
                    system_prompt=SYSTEM_INSTRUCTIONS,
                    user_prompt=user_prompt,
                    schema=schema,
                    max_tokens=8192,
                )
                return ExtractedOpportunity.model_validate(data)
            except (AllAIProvidersUnavailable, ValidationError, ValueError, TypeError) as exc:
                raise RequirementExtractionError(
                    "Gemini and all configured fallback providers failed opportunity analysis"
                ) from exc

        raise RequirementExtractionError(
            f"Gemini opportunity analysis failed: {gemini_error}"
        ) from gemini_error

    def _chunk_source(self, text: str) -> list[str]:
        text = text.strip()
        maximum = self.opportunity_settings.opportunity_analysis_chunk_characters
        overlap = min(
            self.opportunity_settings.opportunity_analysis_chunk_overlap,
            max(0, maximum // 4),
        )
        if len(text) <= maximum:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + maximum)
            if end < len(text):
                split = max(
                    text.rfind("\n\n", start, end),
                    text.rfind("\n", start, end),
                )
                if split > start + maximum // 2:
                    end = split
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
        return chunks

    @staticmethod
    def _normal_key(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

    @classmethod
    def _requirement_key(cls, item: dict[str, Any]) -> tuple[Any, ...]:
        return (
            cls._normal_key(item.get("requirement_type")),
            cls._normal_key(item.get("normalized_value") or item.get("label")),
            item.get("minimum_years"),
            item.get("minimum_count"),
            cls._normal_key(item.get("minimum_degree_level")),
            cls._normal_key(item.get("operator")),
        )

    @classmethod
    def _merge_role(cls, current: dict[str, Any], incoming: dict[str, Any]) -> None:
        current["quantity"] = max(
            int(current.get("quantity") or 1),
            int(incoming.get("quantity") or 1),
        )
        current["is_mandatory"] = bool(current.get("is_mandatory") or incoming.get("is_mandatory"))

        incoming_description = incoming.get("description")
        current_description = current.get("description")
        if isinstance(incoming_description, str) and len(incoming_description) > len(
            str(current_description or "")
        ):
            current["description"] = incoming_description

        existing_requirements = current.get("requirements")
        if not isinstance(existing_requirements, list):
            existing_requirements = []
            current["requirements"] = existing_requirements

        existing_keys = {
            cls._requirement_key(item) for item in existing_requirements if isinstance(item, dict)
        }
        incoming_requirements = incoming.get("requirements")
        if isinstance(incoming_requirements, list):
            for requirement in incoming_requirements:
                if not isinstance(requirement, dict):
                    continue
                key = cls._requirement_key(requirement)
                if key not in existing_keys:
                    existing_requirements.append(requirement)
                    existing_keys.add(key)

    @classmethod
    def _merge_results(
        cls,
        results: list[ExtractedOpportunity],
    ) -> ExtractedOpportunity:
        if not results:
            raise RequirementExtractionError("Opportunity analysis returned no chunks")

        merged = results[0].model_dump(mode="python")
        roles = merged.get("roles")
        if not isinstance(roles, list):
            roles = []
            merged["roles"] = roles
        team_requirements = merged.get("team_requirements")
        if not isinstance(team_requirements, list):
            team_requirements = []
            merged["team_requirements"] = team_requirements

        for result in results[1:]:
            candidate = result.model_dump(mode="python")
            for key in ("title", "client_name", "reference_number", "deadline_at"):
                if not merged.get(key) and candidate.get(key):
                    merged[key] = candidate[key]

            candidate_summary = candidate.get("summary")
            if isinstance(candidate_summary, str) and len(candidate_summary) > len(
                str(merged.get("summary") or "")
            ):
                merged["summary"] = candidate_summary

            role_index = {
                cls._normal_key(item.get("title")): item for item in roles if isinstance(item, dict)
            }
            candidate_roles = candidate.get("roles")
            if isinstance(candidate_roles, list):
                for role in candidate_roles:
                    if not isinstance(role, dict):
                        continue
                    key = cls._normal_key(role.get("title"))
                    current = role_index.get(key)
                    if current is None:
                        roles.append(role)
                        role_index[key] = role
                    else:
                        cls._merge_role(current, role)

            team_keys = {
                cls._requirement_key(item) for item in team_requirements if isinstance(item, dict)
            }
            candidate_team = candidate.get("team_requirements")
            if isinstance(candidate_team, list):
                for requirement in candidate_team:
                    if not isinstance(requirement, dict):
                        continue
                    team_key = cls._requirement_key(requirement)
                    if team_key not in team_keys:
                        team_requirements.append(requirement)
                        team_keys.add(team_key)

        return ExtractedOpportunity.model_validate(merged)
