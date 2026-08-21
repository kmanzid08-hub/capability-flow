from fastapi import APIRouter

from app.api.v1 import (
    auth,
    capabilities,
    documents,
    experiences,
    members,
    opportunities,
    organizations,
    people,
    profile_ai,
)

api_router = APIRouter()


@api_router.get(
    "/health",
    tags=["health"],
)
async def health() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(members.router)
api_router.include_router(people.router)
api_router.include_router(capabilities.router)
api_router.include_router(experiences.router)
api_router.include_router(documents.router)
api_router.include_router(profile_ai.router)
api_router.include_router(opportunities.router)
