import asyncio
import logging
import re
import uuid
from datetime import UTC, date, datetime
from io import BytesIO
from typing import Any

import pymupdf
from fastapi import HTTPException, status
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError
from pypdf import PdfReader
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.partial_dates import PartialDateError, normalize_partial_date
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
from app.services.ai_fallback import AllAIProvidersUnavailable, FallbackAI
from app.services.document_storage import create_document_storage, is_temporary_document_filename
from app.services.document_text import (
    UnsupportedAnalysisDocument,
    extract_embedded_document_images,
    extract_text,
    is_gemini_native_document,
)

logger = logging.getLogger(__name__)


class GeminiTemporarilyUnavailable(RuntimeError):
    pass


class GeminiNoUsableEvidence(RuntimeError):
    pass


class DocumentTextRecoveryUnavailable(RuntimeError):
    pass


CATEGORIES = {"profile", "skill", "education", "certification", "employment", "project"}

GEMINI_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

SYSTEM_PROMPT = """You extract professional capability evidence from documents for a
consulting/audit talent database.

Return valid JSON only. Never invent facts. Use null when a value is not supported by the
document. Each item must be independently reviewable by a human and contain only information
supported by the document. Preserve the precision actually stated in the source. For employment
and project start/end dates, use YYYY when only the year is known, YYYY-MM when the year and month
are known, and YYYY-MM-DD only when the full date is known. Never invent a missing month or day.

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
Extract every reviewable fact that is explicitly supported by the document. A professional CV
will usually contain several skills, education, employment, certifications, projects, or useful
profile details. Do not return empty sections merely because some optional fields are missing.
For employment and project records, keep a source-supported year-only or year-month start date;
those are valid partial dates. Omit the structured record only when no start date at all is
supported.
Still extract all other supported evidence, such as skills, qualifications, clients, sectors,
responsibilities, achievements, and useful profile details. For service attestations, employment
certificates, reference letters, or similar evidence, preserve exactly the date precision stated by
the source. Never invent an exact month or day merely to create a record.
"""


class AIProfileDetails(BaseModel):
    summary: str | None = None
    professional_title: str | None = None
    nationality: str | None = None
    country_of_residence: str | None = None


class AISkill(BaseModel):
    name: str
    proficiency: str | None = None
    years_experience: float | None = None
    last_used_year: int | None = None
    notes: str | None = None
    confidence: float = Field(ge=0, le=1)


class AIEducation(BaseModel):
    degree_level: str
    degree_name: str | None = None
    field_of_study: str | None = None
    institution: str
    country: str | None = None
    start_year: int | None = None
    graduation_year: int | None = None
    notes: str | None = None
    confidence: float = Field(ge=0, le=1)


class AICertification(BaseModel):
    name: str
    issuer: str | None = None
    credential_id: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    verification_url: str | None = None
    notes: str | None = None
    confidence: float = Field(ge=0, le=1)


class AIEmployment(BaseModel):
    employer_name: str
    job_title: str
    employment_type: str | None = None
    industry: str | None = None
    location: str | None = None
    country: str | None = None
    start_date: str
    end_date: str | None = None
    is_current: bool
    description: str | None = None
    responsibilities: str | None = None
    achievements: str | None = None
    confidence: float = Field(ge=0, le=1)


class AIProject(BaseModel):
    project_name: str
    client_name: str | None = None
    role: str
    sector: str | None = None
    location: str | None = None
    country: str | None = None
    start_date: str
    end_date: str | None = None
    is_current: bool
    description: str | None = None
    responsibilities: str | None = None
    outcomes: str | None = None
    skills_summary: str | None = None
    confidence: float = Field(ge=0, le=1)


class AIProfileExtraction(BaseModel):
    profile: AIProfileDetails
    skills: list[AISkill]
    education: list[AIEducation]
    certifications: list[AICertification]
    employment: list[AIEmployment]
    projects: list[AIProject]


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
        self.fallback_ai = FallbackAI(self.settings)

    async def analyze_document(self, person_id: uuid.UUID, document_id: uuid.UUID) -> int:
        person = await self.people.get(person_id)
        document = await self.documents.get(person_id, document_id)

        if person is None or document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Person or document not found",
            )

        if not self.settings.gemini_api_key and not self.fallback_ai.configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "AI analysis is not configured. Add GEMINI_API_KEY, GROQ_API_KEY, "
                    "OPENROUTER_API_KEY, or OPENAI_API_KEY on the backend service."
                ),
            )

        document.analysis_status = DocumentAnalysisStatus.PROCESSING.value
        document.analysis_error = None
        await self.session.commit()

        try:
            if is_temporary_document_filename(document.original_filename):
                raise UnsupportedAnalysisDocument(
                    "This is an Office temporary file, not the original document. "
                    "Delete it and upload the original Word document instead."
                )

            content = await self.storage.read(document.storage_key)
            if not content:
                raise UnsupportedAnalysisDocument(
                    "This document is empty (0 KB). Delete it and upload the original file."
                )
            extension = document.file_extension.lower()

            text: str | None = None
            if not is_gemini_native_document(extension):
                try:
                    text = extract_text(
                        content,
                        extension,
                        self.settings.ai_max_document_chars,
                    )
                except UnsupportedAnalysisDocument as exc:
                    if extension == ".docx" and "No readable text was found" in str(exc):
                        logger.info(
                            "DOCX has no local text; attempting embedded-image recovery: file=%s",
                            document.original_filename,
                        )
                        text = None
                    else:
                        raise

            result = await self._call_ai(
                person=person,
                document=document,
                content=content,
                text=text,
            )
            suggestions = self._build_suggestions(person_id, document_id, result)
            if not suggestions:
                raise GeminiNoUsableEvidence("Gemini returned no reviewable profile evidence.")

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
            document.analysis_error = None
            document.last_analyzed_at = datetime.now(UTC)
            await self.session.commit()
            return len(suggestions)

        except (UnsupportedAnalysisDocument, FileNotFoundError) as exc:
            await self.session.rollback()
            await self._mark_analysis_failed(document_id, str(exc))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        except HTTPException:
            await self.session.rollback()
            raise

        except DocumentTextRecoveryUnavailable as exc:
            logger.warning(
                "Document text recovery unavailable: person_id=%s document_id=%s error=%s",
                person_id,
                document_id,
                str(exc),
            )
            await self.session.rollback()
            message = str(exc)
            await self._mark_analysis_failed(document_id, message)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=message,
            ) from exc

        except GeminiTemporarilyUnavailable as exc:
            logger.warning(
                "Gemini temporarily unavailable after retries: "
                "person_id=%s document_id=%s error=%s",
                person_id,
                document_id,
                str(exc),
            )
            await self.session.rollback()
            message = (
                "AI providers are temporarily unavailable. Your document is safe. "
                "Please retry the analysis in a few minutes."
            )
            await self._mark_analysis_failed(document_id, message)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=message,
            ) from exc

        except GeminiNoUsableEvidence as exc:
            logger.warning(
                "Gemini returned no usable evidence: person_id=%s document_id=%s error=%s",
                person_id,
                document_id,
                str(exc),
            )
            await self.session.rollback()
            message = (
                "AI could not extract reviewable profile evidence from this document. "
                "Your document is safe. Please retry the analysis or review it manually."
            )
            await self._mark_analysis_failed(document_id, message)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=message,
            ) from exc

        except Exception as exc:
            logger.exception(
                "AI document analysis failed: person_id=%s document_id=%s "
                "exception_type=%s error=%s",
                person_id,
                document_id,
                type(exc).__name__,
                str(exc),
            )
            await self.session.rollback()
            await self._mark_analysis_failed(
                document_id,
                "AI analysis failed. Please retry or review the document manually.",
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI analysis failed. Please retry in a moment.",
            ) from exc

    async def _mark_analysis_failed(self, document_id: uuid.UUID, message: str) -> None:
        document = await self.session.get(PersonDocument, document_id)
        if document is None or document.organization_id != self.organization_id:
            return

        document.analysis_status = DocumentAnalysisStatus.FAILED.value
        document.analysis_error = message
        document.last_analyzed_at = datetime.now(UTC)
        await self.session.commit()

    async def _call_ai(
        self,
        person: Person,
        document: PersonDocument,
        content: bytes,
        text: str | None,
    ) -> dict[str, Any]:
        gemini_error: Exception | None = None
        if self.settings.gemini_api_key:
            try:
                return await self._call_gemini(person, document, content, text)
            except (GeminiTemporarilyUnavailable, GeminiNoUsableEvidence) as exc:
                gemini_error = exc
                logger.warning("Gemini exhausted; trying configured fallback providers: %s", exc)
            except Exception as exc:
                gemini_error = exc
                logger.warning("Gemini failed; trying configured fallback providers: %s", exc)

        if not self.fallback_ai.configured:
            if isinstance(gemini_error, GeminiNoUsableEvidence):
                raise gemini_error
            raise GeminiTemporarilyUnavailable(
                "No usable AI provider is currently available"
            ) from gemini_error

        fallback_text = text
        if fallback_text is None and document.file_extension.lower() == ".pdf":
            try:
                reader = PdfReader(BytesIO(content))
                pages = [(page.extract_text() or "").strip() for page in reader.pages]
                fallback_text = "\n\n".join(page for page in pages if page)
                fallback_text = fallback_text[: self.settings.ai_max_document_chars]
            except Exception as exc:
                logger.warning("PDF fallback text extraction failed: %s", str(exc))
                fallback_text = None
        if not self._has_usable_fallback_text(fallback_text):
            fallback_text = await self._recover_image_text(document, content)
        if not fallback_text:
            raise DocumentTextRecoveryUnavailable(
                "AI could not recover readable text from this scanned or image-based document. "
                "The file is safe. Try a clearer scan or a text-searchable PDF, then analyze "
                "it again."
            ) from gemini_error

        chunks = self._chunk_fallback_text(fallback_text)
        results: list[dict[str, Any]] = []
        providers: list[str] = []
        try:
            for index, chunk in enumerate(chunks, start=1):
                user_prompt = (
                    f"Person: {person.display_name}. Current title: "
                    f"{person.professional_title or 'not provided'}. "
                    f"Document type: {document.document_type.value}. "
                    f"File: {document.original_filename}. "
                    f"Document chunk {index} of {len(chunks)}.\n\n"
                    "Extract only evidence belonging to this person. Never treat tender requirements, "  # noqa: E501
                    "other team members, or client staff as this person's experience. Extract every "  # noqa: E501  # noqa: E501
                    "supported fact visible in this chunk; do not infer missing facts.\n\n"
                    f"DOCUMENT TEXT:\n{chunk}"
                )
                data, provider = await self.fallback_ai.generate_json(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    schema=AIProfileExtraction.model_json_schema(),
                    max_tokens=2200,
                )
                parsed = AIProfileExtraction.model_validate(data)
                results.append(parsed.model_dump(mode="json"))
                providers.append(provider)
                logger.info(
                    "Fallback profile chunk completed: chunk=%s/%s provider=%s",
                    index,
                    len(chunks),
                    provider,
                )
            result = self._merge_extractions(results)
            if not self._has_meaningful_evidence(result):
                raise GeminiNoUsableEvidence(
                    "Fallback providers returned no reviewable profile evidence"
                )
            logger.info("Profile extraction completed via fallback providers=%s", providers)
            return result
        except GeminiNoUsableEvidence:
            raise
        except (ValidationError, ValueError, AllAIProvidersUnavailable) as exc:
            raise GeminiTemporarilyUnavailable(
                "All configured AI providers are temporarily unavailable"
            ) from exc

    async def _recover_image_text(
        self,
        document: PersonDocument,
        content: bytes,
    ) -> str | None:
        extension = document.file_extension.lower()
        images: list[tuple[bytes, str, str]] = []

        if extension in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            mime_type = GEMINI_MEDIA_TYPES.get(extension, "image/jpeg")
            images.append((content, mime_type, document.original_filename))
        elif extension == ".pdf":
            images = self._render_pdf_pages(document.original_filename, content)
        elif extension == ".docx":
            embedded = extract_embedded_document_images(
                content,
                extension,
                self.settings.ai_docx_vision_max_images,
            )
            images = [
                (image_data, mime_type, f"{document.original_filename} {label}")
                for image_data, mime_type, label in embedded
            ]
            if images:
                logger.info(
                    "Extracted DOCX images for multimodal fallback: file=%s images=%s",
                    document.original_filename,
                    len(images),
                )

        if not images:
            logger.warning(
                "No page images could be rendered for multimodal fallback: file=%s extension=%s",
                document.original_filename,
                extension,
            )
            return None

        recovered: list[str] = []
        providers: list[str] = []
        provider_failures: list[str] = []
        for image_data, mime_type, label in images:
            try:
                text, provider = await self.fallback_ai.extract_image_text(
                    image_bytes=image_data,
                    mime_type=mime_type,
                    label=label,
                )
                if text.strip():
                    recovered.append(f"[{label}]\n{text.strip()}")
                    providers.append(provider)
            except AllAIProvidersUnavailable as exc:
                provider_failures.append(str(exc))
                logger.warning(
                    "Multimodal fallback unavailable for page image: label=%s error=%s",
                    label,
                    str(exc),
                )

        combined = "\n\n".join(recovered).strip()
        if combined:
            logger.info(
                "Recovered image-based document text: file=%s pages=%s providers=%s",
                document.original_filename,
                len(recovered),
                providers,
            )
            return combined[: self.settings.ai_max_document_chars]

        if provider_failures:
            raise GeminiTemporarilyUnavailable(
                "Configured multimodal AI providers could not read the rendered document pages"
            )
        return None

    def _render_pdf_pages(
        self,
        filename: str,
        content: bytes,
    ) -> list[tuple[bytes, str, str]]:
        images: list[tuple[bytes, str, str]] = []
        try:
            with pymupdf.open(stream=content, filetype="pdf") as pdf:  # type: ignore[no-untyped-call]
                if pdf.page_count == 0:
                    return images

                max_pages = min(pdf.page_count, self.settings.ai_pdf_vision_max_pages)
                if pdf.page_count > max_pages:
                    logger.info(
                        "PDF vision fallback capped pages: file=%s total_pages=%s max_pages=%s",
                        filename,
                        pdf.page_count,
                        max_pages,
                    )

                zoom = self.settings.ai_pdf_render_dpi / 72.0
                matrix = pymupdf.Matrix(zoom, zoom)  # type: ignore[no-untyped-call]
                for page_index in range(max_pages):
                    page = pdf.load_page(page_index)
                    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                    image_data = pixmap.tobytes("jpeg", jpg_quality=85)

                    # Keep individual vision requests bounded. If a complex page is still
                    # unusually large, re-render at a lower resolution before sending it.
                    if len(image_data) > 10 * 1024 * 1024:
                        reduced = pymupdf.Matrix(1.5, 1.5)  # type: ignore[no-untyped-call]
                        pixmap = page.get_pixmap(matrix=reduced, alpha=False)
                        image_data = pixmap.tobytes("jpeg", jpg_quality=78)

                    if not image_data or len(image_data) > 12 * 1024 * 1024:
                        logger.warning(
                            "Skipping oversized rendered PDF page: file=%s page=%s bytes=%s",
                            filename,
                            page_index + 1,
                            len(image_data),
                        )
                        continue

                    images.append(
                        (
                            image_data,
                            "image/jpeg",
                            f"{filename} page {page_index + 1}",
                        )
                    )
        except Exception as exc:
            logger.warning(
                "PDF page rendering failed: file=%s error=%s",
                filename,
                str(exc),
            )
            return []

        logger.info(
            "Rendered PDF pages for multimodal fallback: file=%s pages=%s dpi=%s",
            filename,
            len(images),
            self.settings.ai_pdf_render_dpi,
        )
        return images

    @staticmethod
    def _has_usable_fallback_text(text: str | None) -> bool:
        if not text:
            return False
        normalized = " ".join(text.split())
        alnum = sum(ch.isalnum() for ch in normalized)
        words = [word for word in normalized.split() if any(ch.isalnum() for ch in word)]

        # Short documents can still contain valuable professional evidence,
        # such as a person name and professional title.
        if len(normalized) >= 30 and alnum >= 20 and len(words) >= 4:
            return True

        return len(normalized) >= 120 and alnum >= 80

    @staticmethod
    def _is_hard_gemini_quota_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return (
            "generaterequestsperdayperprojectpermodel" in message
            or "free_tier_requests" in message
            or "perdayperprojectpermodel" in message
        )

    @staticmethod
    def _chunk_fallback_text(text: str, max_chars: int = 8500) -> list[str]:
        text = text.strip()
        if len(text) <= max_chars:
            return [text]
        chunks: list[str] = []
        start = 0
        overlap = 800
        while start < len(text):
            end = min(len(text), start + max_chars)
            if end < len(text):
                split = max(text.rfind("\n\n", start, end), text.rfind("\n", start, end))
                if split > start + max_chars // 2:
                    end = split
            chunks.append(text[start:end].strip())
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
        return [chunk for chunk in chunks if chunk]

    @classmethod
    def _merge_extractions(cls, results: list[dict[str, Any]]) -> dict[str, Any]:
        merged: dict[str, Any] = {
            "profile": {
                "summary": None,
                "professional_title": None,
                "nationality": None,
                "country_of_residence": None,
            },
            "skills": [],
            "education": [],
            "certifications": [],
            "employment": [],
            "projects": [],
        }
        for result in results:
            profile = result.get("profile") or {}
            for key in merged["profile"]:
                candidate = profile.get(key)
                current = merged["profile"].get(key)
                if candidate and (not current or len(str(candidate)) > len(str(current))):
                    merged["profile"][key] = candidate

            for category in ("skills", "education", "certifications", "employment", "projects"):
                for item in result.get(category) or []:
                    if not isinstance(item, dict):
                        continue
                    marker = cls._dedupe_key(category, item)
                    existing_index = next(
                        (
                            i
                            for i, existing in enumerate(merged[category])
                            if cls._dedupe_key(category, existing) == marker
                        ),
                        None,
                    )
                    if existing_index is None:
                        merged[category].append(dict(item))
                    else:
                        merged[category][existing_index] = cls._merge_item(
                            merged[category][existing_index],
                            item,
                        )
        return merged

    @staticmethod
    def _normalize_key(value: Any) -> str:
        return " ".join(str(value or "").lower().split())

    @classmethod
    def _dedupe_key(cls, category: str, item: dict[str, Any]) -> tuple[str, ...]:
        fields = {
            "skills": ("name",),
            "education": ("institution", "degree_name", "field_of_study", "graduation_year"),
            "certifications": ("name", "issuer", "issue_date"),
            "employment": ("employer_name", "job_title", "start_date", "end_date"),
            "projects": ("project_name", "client_name", "role", "start_date"),
        }[category]
        return tuple(cls._normalize_key(item.get(field)) for field in fields)

    @staticmethod
    def _merge_item(existing: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        merged = dict(existing)
        for key, value in candidate.items():
            if value in (None, "", [], {}):
                continue
            current = merged.get(key)
            if current in (None, "", [], {}):
                merged[key] = value
                continue
            if key == "confidence":
                try:
                    merged[key] = max(current, value)
                except (TypeError, ValueError):
                    pass
            elif isinstance(value, str) and isinstance(current, str) and len(value) > len(current):
                merged[key] = value
        return merged

    async def _call_gemini(
        self,
        person: Person,
        document: PersonDocument,
        content: bytes,
        text: str | None,
    ) -> dict[str, Any]:
        prompt = (
            f"Person already entered by the employee: {person.display_name}. "
            f"Current title: {person.professional_title or 'not provided'}. "
            f"Document type: {document.document_type.value}. "
            f"File: {document.original_filename}.\n\n"
            "Extract only evidence that belongs to this person. Do not treat tender "
            "requirements, other team members, or client staff as the person's own "
            "experience. Return every reviewable fact explicitly supported by the document."
        )

        extension = document.file_extension.lower()
        base_parts: list[types.Part] = []
        if extension in GEMINI_MEDIA_TYPES:
            base_parts.append(
                types.Part.from_bytes(data=content, mime_type=GEMINI_MEDIA_TYPES[extension])
            )
            base_parts.append(types.Part.from_text(text=prompt))
        elif text is not None:
            base_parts.append(types.Part.from_text(text=f"{prompt}\n\nDOCUMENT TEXT:\n{text}"))
        else:
            raise UnsupportedAnalysisDocument(
                f"AI extraction is not available for {extension or 'this file type'} yet."
            )

        transient_status_codes = {429, 500, 502, 503, 504}
        retry_delays = (0.0, 2.0, 5.0)
        last_error: Exception | None = None

        for attempt, delay in enumerate(retry_delays, start=1):
            if delay:
                await asyncio.sleep(delay)

            attempt_parts = list(base_parts)
            if attempt > 1:
                attempt_parts.append(
                    types.Part.from_text(
                        text=(
                            "Previous extraction attempts were unusable or contained no "
                            "reviewable evidence. Re-read the entire document carefully. "
                            "Extract all explicitly supported profile details, skills, "
                            "education, certifications, employment, and projects. Do not "
                            "invent missing facts, but do not leave supported evidence out."
                        )
                    )
                )

            request_content = types.Content(role="user", parts=attempt_parts)

            try:
                async with genai.Client(api_key=self.settings.gemini_api_key).aio as client:
                    response = await client.models.generate_content(
                        model=self.settings.ai_model,
                        contents=request_content,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            response_mime_type="application/json",
                            response_schema=AIProfileExtraction,
                            max_output_tokens=6000,
                            temperature=0.1,
                        ),
                    )

                cleaned = (response.text or "").strip()
                if not cleaned:
                    last_error = ValueError("Gemini returned an empty response")
                    logger.warning(
                        "Gemini returned empty output on attempt %s/%s",
                        attempt,
                        len(retry_delays),
                    )
                    continue

                try:
                    parsed = AIProfileExtraction.model_validate_json(cleaned)
                except (ValidationError, ValueError) as exc:
                    last_error = exc
                    logger.warning(
                        "Gemini returned invalid structured output on attempt %s/%s: %s",
                        attempt,
                        len(retry_delays),
                        str(exc),
                    )
                    continue

                data = parsed.model_dump(mode="json")
                counts = self._extraction_counts(data)
                logger.info(
                    "Gemini extraction counts: person_id=%s document_id=%s "
                    "profile=%s skills=%s education=%s certifications=%s "
                    "employment=%s projects=%s",
                    person.id,
                    document.id,
                    counts["profile"],
                    counts["skills"],
                    counts["education"],
                    counts["certifications"],
                    counts["employment"],
                    counts["projects"],
                )

                if not self._has_meaningful_evidence(data):
                    last_error = GeminiNoUsableEvidence(
                        "Gemini returned a valid but empty structured extraction."
                    )
                    logger.warning(
                        "Gemini returned no reviewable evidence on attempt %s/%s",
                        attempt,
                        len(retry_delays),
                    )
                    continue

                return data

            except Exception as exc:
                status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                if self._is_hard_gemini_quota_error(exc):
                    logger.warning(
                        "Gemini daily quota exhausted; switching immediately to fallback providers"
                    )
                    raise GeminiTemporarilyUnavailable("Gemini daily quota is exhausted") from exc
                if status_code not in transient_status_codes:
                    raise
                last_error = exc
                logger.warning(
                    "Transient Gemini failure on attempt %s/%s: status=%s error=%s",
                    attempt,
                    len(retry_delays),
                    status_code,
                    str(exc),
                )

        if isinstance(last_error, GeminiNoUsableEvidence):
            raise last_error

        raise GeminiTemporarilyUnavailable(
            "Gemini did not return a usable structured response after automatic retries."
        ) from last_error

    @staticmethod
    def _extraction_counts(data: dict[str, Any]) -> dict[str, int]:
        profile = data.get("profile")
        profile_count = (
            1 if isinstance(profile, dict) and any(profile.get(key) for key in profile) else 0
        )

        def item_count(key: str) -> int:
            value = data.get(key)
            return len(value) if isinstance(value, list) else 0

        return {
            "profile": profile_count,
            "skills": item_count("skills"),
            "education": item_count("education"),
            "certifications": item_count("certifications"),
            "employment": item_count("employment"),
            "projects": item_count("projects"),
        }

    @classmethod
    def _has_meaningful_evidence(cls, data: dict[str, Any]) -> bool:
        counts = cls._extraction_counts(data)
        return any(counts.values())

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
                if category in {"employment", "project"}:
                    payload = self._normalize_experience_payload(payload, category)
                elif category == "certification":
                    payload["issue_date"] = self._normalize_date_value(payload.get("issue_date"))
                    payload["expiry_date"] = self._normalize_date_value(payload.get("expiry_date"))
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

            suggestion.status = "accepted"
            suggestion.applied_entity_id = entity_id
            suggestion.reviewed_by_user_id = self.user_id
            suggestion.reviewed_at = datetime.now(UTC)

            if entity_id is not None:
                await self._ensure_evidence_link(
                    person_id=person_id,
                    document_id=suggestion.source_document_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )

            await self.session.commit()
        except ValidationError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=self._format_validation_error(exc),
            ) from exc
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception as exc:
            await self.session.rollback()
            logger.exception(
                "Accepting AI suggestion failed: person_id=%s suggestion_id=%s error=%s",
                person_id,
                suggestion_id,
                str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This suggestion could not be saved, but previously accepted profile "
                    "information is safe. Please retry this item."
                ),
            ) from exc

        suggestion = await self._get_suggestion(person_id, suggestion_id)
        await self._refresh_document_status(suggestion.source_document_id)
        return suggestion

    async def accept_all(self, person_id: uuid.UUID) -> dict[str, Any]:
        pending_result = await self.session.scalars(
            select(ProfileSuggestion)
            .where(
                ProfileSuggestion.organization_id == self.organization_id,
                ProfileSuggestion.person_id == person_id,
                ProfileSuggestion.status == "pending",
            )
            .order_by(ProfileSuggestion.created_at.asc())
        )
        pending = list(pending_result)
        pending_items = [(suggestion.id, suggestion.title) for suggestion in pending]

        accepted = 0
        failures: list[dict[str, str]] = []

        for suggestion_id, suggestion_title in pending_items:
            try:
                await self.accept(person_id, suggestion_id)
                accepted += 1
            except HTTPException as exc:
                await self.session.rollback()
                detail = exc.detail
                if isinstance(detail, str):
                    message = detail
                else:
                    message = "This suggestion needs manual review before it can be saved."
                failures.append(
                    {
                        "suggestion_id": str(suggestion_id),
                        "title": suggestion_title,
                        "detail": message,
                    }
                )
                logger.warning(
                    "Accept-all skipped one suggestion and continued: "
                    "person_id=%s suggestion_id=%s detail=%s",
                    person_id,
                    suggestion_id,
                    message,
                )
            except Exception as exc:
                await self.session.rollback()
                message = "This suggestion could not be saved and needs manual review."
                failures.append(
                    {
                        "suggestion_id": str(suggestion_id),
                        "title": suggestion_title,
                        "detail": message,
                    }
                )
                logger.exception(
                    "Accept-all encountered an unexpected error and continued: "
                    "person_id=%s suggestion_id=%s error=%s",
                    person_id,
                    suggestion_id,
                    str(exc),
                )

        return {
            "total": len(pending_items),
            "accepted": accepted,
            "failed": len(failures),
            "failures": failures,
        }

    @staticmethod
    def _normalize_date_value(value: Any) -> Any:
        """Normalize only dates that are already explicit; never invent missing precision."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if not isinstance(value, str):
            return value

        cleaned = value.strip()
        if not cleaned:
            return None

        if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ].*)?", cleaned):
            explicit_date = cleaned[:10]
            try:
                date.fromisoformat(explicit_date)
            except ValueError:
                return cleaned
            return explicit_date

        # Partial dates such as 2020, 2020-05, or Jan 2020 are deliberately
        # retained unchanged so validation can send the item to human review.
        return cleaned

    @classmethod
    def _normalize_experience_payload(
        cls,
        payload: dict[str, Any],
        category: str,
    ) -> dict[str, Any]:
        normalized = dict(payload)
        for field in ("start_date", "end_date"):
            value = normalized.get(field)
            try:
                normalized[field] = normalize_partial_date(value)
            except PartialDateError:
                # Preserve ambiguous source text for human review rather than guessing.
                normalized[field] = cls._normalize_date_value(value)

        if normalized.get("end_date") is not None and normalized.get("is_current") is True:
            normalized["is_current"] = False

        if category == "employment":
            raw_type = normalized.get("employment_type")
            if isinstance(raw_type, str):
                canonical = re.sub(r"[\s-]+", "_", raw_type.strip().lower())
                allowed = {
                    "full_time",
                    "part_time",
                    "contract",
                    "consulting",
                    "temporary",
                    "internship",
                    "volunteer",
                    "other",
                }
                normalized["employment_type"] = canonical if canonical in allowed else None

        return normalized

    @staticmethod
    def _format_validation_error(exc: ValidationError) -> str:
        """Turn Pydantic errors into review instructions that are useful in the UI."""
        labels = {
            "start_date": "Start date",
            "end_date": "End date",
            "issue_date": "Issue date",
            "expiry_date": "Expiry date",
            "employer_name": "Employer",
            "job_title": "Job title",
            "project_name": "Project name",
            "role": "Role",
            "institution": "Institution",
            "name": "Name",
        }
        messages: list[str] = []

        for error in exc.errors():
            loc = error.get("loc") or ()
            field = str(loc[-1]) if loc else ""
            label = labels.get(field, field.replace("_", " ").title() if field else "Record")
            input_value = error.get("input")
            message = str(error.get("msg") or "Invalid value")

            if field in {"start_date", "end_date"}:
                shown = f" '{input_value}'" if input_value not in (None, "") else ""
                rendered = (
                    f"{label}{shown} is not a supported experience date. "
                    "Use YYYY, YYYY-MM, or YYYY-MM-DD exactly as supported by the source. "
                    "Do not invent a missing month or day."
                )
            elif field in {"issue_date", "expiry_date"}:
                shown = f" '{input_value}'" if input_value not in (None, "") else ""
                rendered = (
                    f"{label}{shown} is not a complete valid date. "
                    "Enter YYYY-MM-DD from the supporting evidence, or leave it blank "
                    "when the date is genuinely not stated."
                )
            elif "End date cannot be earlier than start date" in message:
                rendered = (
                    "End date is earlier than start date. Review the source document and "
                    "correct the two dates before accepting."
                )
            elif "Current employment cannot have an end date" in message:
                rendered = "Current employment cannot also have an end date. Review the dates."
            elif "Current project cannot have an end date" in message:
                rendered = "An ongoing project cannot also have an end date. Review the dates."
            else:
                rendered = f"{label}: {message}. Edit this suggestion before accepting."

            if rendered not in messages:
                messages.append(rendered)

        return " ".join(messages) or "This suggestion needs manual review before it can be saved."

    async def _ensure_evidence_link(
        self,
        person_id: uuid.UUID,
        document_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> None:
        existing_link = await self.session.scalar(
            select(EvidenceLink.id).where(
                EvidenceLink.organization_id == self.organization_id,
                EvidenceLink.person_id == person_id,
                EvidenceLink.document_id == document_id,
                EvidenceLink.entity_type == entity_type,
                EvidenceLink.entity_id == entity_id,
            )
        )
        if existing_link is not None:
            return

        self.session.add(
            EvidenceLink(
                organization_id=self.organization_id,
                person_id=person_id,
                document_id=document_id,
                entity_type=entity_type,
                entity_id=entity_id,
                created_by_user_id=self.user_id,
            )
        )

    async def _apply(
        self,
        person_id: uuid.UUID,
        suggestion: ProfileSuggestion,
    ) -> tuple[str, uuid.UUID | None]:
        payload = dict(suggestion.payload)

        if suggestion.category in {"employment", "project"}:
            payload = self._normalize_experience_payload(payload, suggestion.category)
            suggestion.payload = payload

            if payload.get("end_date") is not None and payload.get("is_current") is False:
                logger.debug(
                    "Normalized AI experience suggestion before validation: "
                    "person_id=%s suggestion_id=%s category=%s",
                    person_id,
                    suggestion.id,
                    suggestion.category,
                )
        elif suggestion.category == "certification":
            payload["issue_date"] = self._normalize_date_value(payload.get("issue_date"))
            payload["expiry_date"] = self._normalize_date_value(payload.get("expiry_date"))
            suggestion.payload = payload

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
