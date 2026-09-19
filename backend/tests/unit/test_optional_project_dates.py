from app.schemas.experience import ProjectCreate


def test_project_create_accepts_missing_start_date_without_fabrication() -> None:
    project = ProjectCreate.model_validate(
        {
            "project_name": "Youth engagement in agribusiness research",
            "client_name": "IITA & IFAD",
            "role": "Researcher",
            "start_date": None,
            "end_date": None,
            "is_current": False,
        }
    )

    assert project.start_date is None
    assert project.end_date is None
