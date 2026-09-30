import pytest
from unittest.mock import MagicMock
from db.database import init_db, get_campaign_tasks
from orchestrator.orchestrator import run_orchestrator
from orchestrator.prompt_templates import (
    OrchestratorResponse,
    AngleTask,
    DesignSystem,
    CopyBrief,
    VALID_FRAMEWORKS,
)


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_orchestrator.db")
    init_db(db_file)
    return db_file


def test_orchestrator_seeds_five_tasks(temp_db):
    # 1. Build a mock parsed response conforming to OrchestratorResponse
    mock_tasks = []
    for fw in VALID_FRAMEWORKS:
        mock_tasks.append(
            AngleTask(
                angle_name=f"{fw.capitalize()} Angle",
                target_persona="Test user persona",
                framework=fw,
                design_system=DesignSystem(
                    brand_color="#111111",
                    canvas_theme="light",
                    cta_color="#FF0000",
                    typography_mood="modern",
                    layout_hierarchy="grid",
                ),
                copy_brief=CopyBrief(
                    hero_headline="Test Headline",
                    subheadline="Test Subheadline",
                    key_benefits=["Benefit 1", "Benefit 2", "Benefit 3"],
                    cta_label="Explore Now",
                ),
            )
        )

    mock_response = OrchestratorResponse(
        product_core_insight="Core problem solved cleanly.",
        tasks=mock_tasks,
    )

    # 2. Mock the OpenAI client beta chat completions parse call
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(parsed=mock_response))]
    mock_client.beta.chat.completions.parse.return_value = mock_completion

    # 3. Run the orchestrator
    campaign_id = run_orchestrator(
        product_name="Solace Cold Brew",
        target_audience="Urban professionals",
        primary_goal="Pre-orders",
        brand_notes="Eco-friendly",
        db_path=temp_db,
        client=mock_client,
    )

    # 4. Verify SQLite state
    assert campaign_id.startswith("camp_")
    tasks = get_campaign_tasks(campaign_id, db_path=temp_db)

    assert len(tasks) == 5
    assigned_frameworks = {t["framework"] for t in tasks}
    assert assigned_frameworks == set(VALID_FRAMEWORKS)
    assert all(t["status"] == "pending" for t in tasks)