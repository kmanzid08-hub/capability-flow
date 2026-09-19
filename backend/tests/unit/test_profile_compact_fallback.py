from app.services.profile_ai import AICompactEvidence, AICompactEvidenceChunk, ProfileAIService


def test_compact_evidence_maps_to_local_profile_shape() -> None:
    compact = AICompactEvidenceChunk(
        evidence=[
            AICompactEvidence(category="skill", title="Caseware Working Papers", confidence=0.95),
            AICompactEvidence(
                category="employment",
                title="Audit Manager",
                organization="UT CPA LTD",
                role="Audit Manager",
                start_date="2021",
                details="Conduct of audits and assurance work.",
                confidence=0.9,
            ),
            AICompactEvidence(
                category="certification",
                title="ACCA",
                organization="ACCA",
                start_date="2020-04",
                confidence=0.9,
            ),
        ]
    )
    result = ProfileAIService._compact_evidence_to_extraction(compact)

    assert result.skills[0].name == "Caseware Working Papers"
    assert result.employment[0].employer_name == "UT CPA LTD"
    assert result.employment[0].start_date == "2021"
    assert result.certifications[0].issue_date == "2020-04"


def test_compact_undated_experience_is_not_mapped_to_unsavable_records() -> None:
    compact = AICompactEvidenceChunk(
        evidence=[
            AICompactEvidence(
                category="project",
                title="Financial literacy training materials",
                organization="Rwanda Environment Management Authority",
                role="Trainer",
                confidence=0.97,
            ),
            AICompactEvidence(
                category="employment",
                title="Research consultant",
                organization="Example Institute",
                role="Research consultant",
                confidence=0.92,
            ),
            AICompactEvidence(
                category="project",
                title="Dated project",
                organization="Example Client",
                role="Lead",
                start_date="2024",
                confidence=0.9,
            ),
        ]
    )

    result = ProfileAIService._compact_evidence_to_extraction(compact)

    assert result.employment == []
    assert len(result.projects) == 1
    assert result.projects[0].project_name == "Dated project"
    assert result.projects[0].start_date == "2024"
