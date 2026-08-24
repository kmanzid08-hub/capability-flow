import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from anthropic import AsyncAnthropic
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.capability import PersonCertification, PersonEducation, PersonSkill
from app.models.document import PersonDocument
from app.models.enums import DocumentAnalysisStatus
from app.models.experience import EmploymentExperience, ProjectExperience
from app.models.person import Person
from app.models.profile_ai import EvidenceLink, ProfileSuggestion
from app.repositories.documents import DocumentRepository
from app.repositories.people import PersonRepository
from app.schemas.capability import CertificationCreate, EducationCreate, SkillCreate
from app.schemas.experience import EmploymentCreate, ProjectCreate
from app.services.document_storage import create_document_storage
from app.services.document_text import UnsupportedAnalysisDocument, extract_text

logger = logging.getLogger(__name__)


CATEGORIES = {"profile", "skill", "education", "certification", "employment", "project"}

SYSTEM_PROMPT = """You extract professional capability evidence from documents for a
consulting/audit talent database.

Return valid JSON only. Never invent facts. Use null when a value is not supported by the
document. Each item must be independently reviewable by a human and contain only information
supported by the document. Dates must use YYYY-MM-DD where a full date is known. Do not infer
exact dates from years. For employment/project records, if only a year is known, omit the record
unless a usable start date is explicit.

Return this JSON structure:
{
  "profile": {
    "summary": string|null,
    "professional_title": string|null,
    "nationality": string|null,
    "country_of_residence": string|null
  },
  "skills": [
    {
      "name": string,
      "proficiency": "beginner"|"intermediate"|"advanced"|"expert"|null,
      "years_experience": number|null,
      "last_used_year": number|null,
      "notes": string|null,
      "confidence": number
    }
  ],
  "education": [
    {
      "degree_level": "secondary"|"certificate"|"diploma"|"associate"|"bachelor"|
        "master"|"doctorate"|"professional"|"other",
      "degree_name": string|null,
      "field_of_study": string|null,
      "institution": string,
      "country": string|null,
      "start_year": number|null,
      "graduation_year": number|null,
      "notes": string|null,
      "confidence": number
    }
  ],
  "certifications": [
    {
      "name": string,
      "issuer": string|null,
      "credential_id": string|null,
      "issue_date": string|null,
      "expiry_date": string|null,
      "verification_url": string|null,
      "notes": string|null,
      "confidence": number
    }
  ],
  "employment": [
    {
      "employer_name": string,
      "job_title": string,
      "employment_type": "full_time"|"part_time"|"contract"|"consulting"|"temporary"|
        "internship"|"volunteer"|"other"|null,
      "industry": string|null,
      "location": string|null,
      "country": string|null,
      "start_date": string,
      "end_date": string|null,
      "is_current": boolean,
      "description": string|null,
      "responsibilities": string|null,
      "achievements": string|null,
      "confidence": number
    }
  ],
  "projects": [
    {
      "project_name": string,
      "client_name": string|null,
      "role": string,
      "sector": string|null,
      "location": string|null,
      "country": string|null,
      "start_date": string,
      "end_date": string|null,
      "is_current": boolean,
      "description": string|null,
      "responsibilities": string|null,
      "outcomes": string|null,
      "skills_summary": string|null,
      "confidence": number
    }
  ]
}

Confidence must be between 0 and 1. Keep summaries concise and factual.
"""


class ProfileAIService:
    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.organization_id = organization_id
        self.user_id = user_id
        self.settings = get_settings()
        self.documents = DocumentRepository(session, organization_id)
        self.people = PersonRepository(session, organization_id)
        self.storage = create_document_storage(self.settings)

    async def analyze_document(self, person_id: uuid.UUID, document_id: uuid.UUID) -> int:
        person = await self.people.get(person_id)
        document = await self.documents.get(person_id, document_id)
        if person is None or document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Person or document not found",
            )
        if not self.settings.anthropic_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "AI analysis is not configured yet. Add ANTHROPIC_API_KEY on the "
                    "backend service."
                ),
            )

        document.analysis_status = DocumentAnalysisStatus.PROCESSING.value
        document.analysis_error = None
        await self.session.commit()

        try:
            content = await self.storage.read(document.storage_key)
            text = extract_text(
                content,
                document.file_extension,
                self.settings.ai_max_document_chars,
            )
            result = await self._call_claude(person, document, text)
            suggestions = self._build_suggestions(person_id, document_id, result)

            existing = await self.session.scalars(
                select(ProfileSuggestion).where(
                    ProfileSuggestion.organization_id == self.organization_id,
                    ProfileSuggestion.person_id == person_id,
                    ProfileSuggestion.source_document_id == document_id,
                    ProfileSuggestion.status == "pending",
                )
            )
            for suggestion in existing:
                await self.session.delete(suggestion)
            for suggestion in suggestions:
                self.session.add(suggestion)

            document.analysis_status = (
                DocumentAnalysisStatus.READY_FOR_REVIEW.value
                if suggestions
                else DocumentAnalysisStatus.COMPLETE.value
            )
            document.last_analyzed_at = datetime.now(UTC)
            await self.session.commit()
            return len(suggestions)
        except (UnsupportedAnalysisDocument, FileNotFoundError) as exc:
            document.analysis_status = DocumentAnalysisStatus.FAILED.value
            document.analysis_error = str(exc)
            document.last_analyzed_at = datetime.now(UTC)
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "AI document analysis failed: person_id=%s document_id=%s "
                "exception_type=%s error=%s",
                person_id,
                document_id,
                type(exc).__name__,
                str(exc),
            )
            document.analysis_status = DocumentAnalysisStatus.FAILED.value
            document.analysis_error = (
                "AI analysis failed. Please retry or review the document manually."
            )
            document.last_analyzed_at = datetime.now(UTC)
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI analysis failed. Please retry in a moment.",
            ) from exc

    async def _call_claude(
        self,
        person: Person,
        document: PersonDocument,
        text: str,
    ) -> dict[str, Any]:
        client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        prompt = (
            f"Person already entered by the employee: {person.display_name}. "
            f"Current title: {person.professional_title or 'not provided'}. "
            f"Document type: {document.document_type.value}. "
            f"File: {document.original_filename}.\n\n"
            "Extract only evidence that belongs to this person. Do not treat tender "
            "requirements, other team members, or client staff as the person's own "
            "experience.\n\nDOCUMENT TEXT:\n" + text
        )
        message = await client.messages.create(
            model=self.settings.ai_model,
            max_tokens=6000,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        text_parts: list[str] = []
        for block in message.content:
            if getattr(block, "type", None) != "text":
                continue
            block_text = getattr(block, "text", None)
            if isinstance(block_text, str):
                text_parts.append(block_text)

        cleaned = "".join(text_parts).strip()
        if cleaned.startswith("```"):
            cleaned = (
                cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            )
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("AI response was not an object")
        return data

    def _build_suggestions(
        self,
        person_id: uuid.UUID,
        document_id: uuid.UUID,
        data: dict[str, Any],
    ) -> list[ProfileSuggestion]:
        rows: list[ProfileSuggestion] = []

        profile = data.get("profile")
        if isinstance(profile, dict) and any(profile.get(key) for key in profile):
            rows.append(
                self._suggestion(
                    person_id,
                    document_id,
                    "profile",
                    "Profile details",
                    profile,
                    0.9,
                )
            )

        mappings = [
            ("skills", "skill", "name"),
            ("education", "education", "degree_name"),
            ("certifications", "certification", "name"),
            ("employment", "employment", "job_title"),
            ("projects", "project", "project_name"),
        ]
        for source_key, category, title_key in mappings:
            items = data.get(source_key, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                payload = dict(item)
                confidence_value = payload.pop("confidence", None)
                confidence = (
                    float(confidence_value) if isinstance(confidence_value, (int, float)) else None
                )
                title = str(payload.get(title_key) or category.title())[:250]
                rows.append(
                    self._suggestion(
                        person_id,
                        document_id,
                        category,
                        title,
                        payload,
                        confidence,
                    )
                )
        return rows

    def _suggestion(
        self,
        person_id: uuid.UUID,
        document_id: uuid.UUID,
        category: str,
        title: str,
        payload: dict[str, Any],
        confidence: float | None,
    ) -> ProfileSuggestion:
        return ProfileSuggestion(
            organization_id=self.organization_id,
            person_id=person_id,
            source_document_id=document_id,
            category=category,
            title=title,
            payload=payload,
            confidence=(max(0.0, min(1.0, confidence)) if confidence is not None else None),
            status="pending",
            created_by_user_id=self.user_id,
        )

    async def list_suggestions(
        self,
        person_id: uuid.UUID,
        status_filter: str | None = None,
    ) -> list[ProfileSuggestion]:
        query = select(ProfileSuggestion).where(
            ProfileSuggestion.organization_id == self.organization_id,
            ProfileSuggestion.person_id == person_id,
        )
        if status_filter:
            query = query.where(ProfileSuggestion.status == status_filter)
        result = await self.session.scalars(query.order_by(ProfileSuggestion.created_at.desc()))
        return list(result)

    async def edit_suggestion(
        self,
        person_id: uuid.UUID,
        suggestion_id: uuid.UUID,
        values: dict[str, Any],
    ) -> ProfileSuggestion:
        suggestion = await self._get_suggestion(person_id, suggestion_id)
        if suggestion.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending suggestions can be edited",
            )
        for key in ("title", "payload", "review_note"):
            if key in values and values[key] is not None:
                setattr(suggestion, key, values[key])
        await self.session.commit()
        await self.session.refresh(suggestion)
        return suggestion

    async def reject(
        self,
        person_id: uuid.UUID,
        suggestion_id: uuid.UUID,
        note: str | None = None,
    ) -> ProfileSuggestion:
        suggestion = await self._get_suggestion(person_id, suggestion_id)
        if suggestion.status != "pending":
            return suggestion
        suggestion.status = "rejected"
        suggestion.review_note = note or suggestion.review_note
        suggestion.reviewed_by_user_id = self.user_id
        suggestion.reviewed_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(suggestion)
        await self._refresh_document_status(suggestion.source_document_id)
        return suggestion

    async def accept(
        self,
        person_id: uuid.UUID,
        suggestion_id: uuid.UUID,
    ) -> ProfileSuggestion:
        suggestion = await self._get_suggestion(person_id, suggestion_id)
        if suggestion.status != "pending":
            return suggestion
        try:
            entity_type, entity_id = await self._apply(person_id, suggestion)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=exc.errors(),
            ) from exc

        suggestion.status = "accepted"
        suggestion.applied_entity_id = entity_id
        suggestion.reviewed_by_user_id = self.user_id
        suggestion.reviewed_at = datetime.now(UTC)
        if entity_id is not None:
            self.session.add(
                EvidenceLink(
                    organization_id=self.organization_id,
                    person_id=person_id,
                    document_id=suggestion.source_document_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    created_by_user_id=self.user_id,
                )
            )
        await self.session.commit()
        await self.session.refresh(suggestion)
        await self._refresh_document_status(suggestion.source_document_id)
        return suggestion

    async def _apply(
        self,
        person_id: uuid.UUID,
        suggestion: ProfileSuggestion,
    ) -> tuple[str, uuid.UUID | None]:
        payload = suggestion.payload

        if suggestion.category == "profile":
            person = await self.people.get(person_id)
            if person is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Person not found",
                )
            for field in (
                "summary",
                "professional_title",
                "nationality",
                "country_of_residence",
            ):
                value = payload.get(field)
                if value and not getattr(person, field):
                    setattr(person, field, str(value))
            person.updated_by_user_id = self.user_id
            return "profile", person.id

        if suggestion.category == "skill":
            skill_data = SkillCreate.model_validate(payload)
            existing_skill = await self.session.scalar(
                select(PersonSkill).where(
                    PersonSkill.organization_id == self.organization_id,
                    PersonSkill.person_id == person_id,
                    func.lower(PersonSkill.name) == skill_data.name.lower(),
                )
            )
            if existing_skill:
                return "skill", existing_skill.id
            skill_entity = PersonSkill(
                organization_id=self.organization_id,
                person_id=person_id,
                **skill_data.model_dump(),
            )
            self.session.add(skill_entity)
            await self.session.flush()
            return "skill", skill_entity.id

        if suggestion.category == "education":
            education_data = EducationCreate.model_validate(payload)
            education_entity = PersonEducation(
                organization_id=self.organization_id,
                person_id=person_id,
                **education_data.model_dump(),
            )
            self.session.add(education_entity)
            await self.session.flush()
            return "education", education_entity.id

        if suggestion.category == "certification":
            certification_data = CertificationCreate.model_validate(payload)
            certification_values = certification_data.model_dump(mode="python")
            if certification_values.get("verification_url") is not None:
                certification_values["verification_url"] = str(
                    certification_values["verification_url"]
                )
            certification_entity = PersonCertification(
                organization_id=self.organization_id,
                person_id=person_id,
                **certification_values,
            )
            self.session.add(certification_entity)
            await self.session.flush()
            return "certification", certification_entity.id

        if suggestion.category == "employment":
            employment_data = EmploymentCreate.model_validate(payload)
            employment_entity = EmploymentExperience(
                organization_id=self.organization_id,
                person_id=person_id,
                **employment_data.model_dump(),
            )
            self.session.add(employment_entity)
            await self.session.flush()
            return "employment", employment_entity.id

        if suggestion.category == "project":
            project_data = ProjectCreate.model_validate(payload)
            project_entity = ProjectExperience(
                organization_id=self.organization_id,
                person_id=person_id,
                **project_data.model_dump(),
            )
            self.session.add(project_entity)
            await self.session.flush()
            return "project", project_entity.id

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported suggestion category: {suggestion.category}",
        )

    async def _get_suggestion(
        self,
        person_id: uuid.UUID,
        suggestion_id: uuid.UUID,
    ) -> ProfileSuggestion:
        suggestion = await self.session.scalar(
            select(ProfileSuggestion).where(
                ProfileSuggestion.id == suggestion_id,
                ProfileSuggestion.organization_id == self.organization_id,
                ProfileSuggestion.person_id == person_id,
            )
        )
        if suggestion is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggestion not found",
            )
        return suggestion

    async def _refresh_document_status(self, document_id: uuid.UUID) -> None:
        pending = await self.session.scalar(
            select(func.count(ProfileSuggestion.id)).where(
                ProfileSuggestion.organization_id == self.organization_id,
                ProfileSuggestion.source_document_id == document_id,
                ProfileSuggestion.status == "pending",
            )
        )
        document = await self.session.get(PersonDocument, document_id)
        if document and document.organization_id == self.organization_id:
            document.analysis_status = (
                DocumentAnalysisStatus.READY_FOR_REVIEW.value
                if pending
                else DocumentAnalysisStatus.COMPLETE.value
            )
            await self.session.commit()

    async def completeness(self, person_id: uuid.UUID) -> dict[str, Any]:
        person = await self.people.get(person_id)
        if person is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Person not found",
            )

        skill_count = await self._count(PersonSkill, person_id)
        education_count = await self._count(PersonEducation, person_id)
        cert_count = await self._count(PersonCertification, person_id)
        employment_count = await self._count(EmploymentExperience, person_id)
        project_count = await self._count(ProjectExperience, person_id)
        document_count = (
            await self.session.scalar(
                select(func.count(PersonDocument.id)).where(
                    PersonDocument.organization_id == self.organization_id,
                    PersonDocument.person_id == person_id,
                )
            )
            or 0
        )

        sections = {
            "identity": bool(person.first_name and person.last_name),
            "contact_or_location": bool(
                person.primary_email or person.primary_phone or person.country_of_residence
            ),
            "availability": person.availability_status.value != "unknown",
            "summary": bool(person.summary),
            "documents": document_count > 0,
            "skills": skill_count > 0,
            "education": education_count > 0,
            "certifications": cert_count > 0,
            "experience": employment_count > 0 or project_count > 0,
        }
        profile_percent = round(100 * sum(sections.values()) / len(sections))
        total_structured = (
            skill_count + education_count + cert_count + employment_count + project_count
        )
        evidence_backed = (
            await self.session.scalar(
                select(func.count(EvidenceLink.id)).where(
                    EvidenceLink.organization_id == self.organization_id,
                    EvidenceLink.person_id == person_id,
                )
            )
            or 0
        )
        evidence_percent = (
            round(100 * min(evidence_backed, total_structured) / total_structured)
            if total_structured
            else 0
        )
        return {
            "profile_percent": profile_percent,
            "evidence_percent": evidence_percent,
            "sections": sections,
            "evidence_backed_records": evidence_backed,
            "total_structured_records": total_structured,
        }

    async def _count(self, model: Any, person_id: uuid.UUID) -> int:
        value = await self.session.scalar(
            select(func.count(model.id)).where(
                model.organization_id == self.organization_id,
                model.person_id == person_id,
            )
        )
        return int(value or 0)
