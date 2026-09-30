import json
import os
import sys
import tempfile
import sqlite3
from pathlib import Path
from typing import Any, Dict, Generator
import pytest

# Ensure project root is always accessible across all tests
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import init_db, insert_task, create_campaign


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Provides a fresh isolated temporary directory per test."""
    with tempfile.TemporaryDirectory() as tmp_path:
        yield tmp_path


@pytest.fixture
def temp_db(temp_dir: str) -> Generator[str, None, None]:
    """Initializes a clean SQLite blackboard database inside an isolated temporary directory."""
    db_path = os.path.join(temp_dir, "test_blackboard.db")
    init_db(db_path)
    yield db_path


@pytest.fixture
def temp_env(temp_dir: str) -> Generator[Dict[str, str], None, None]:
    """
    Provides both an isolated blackboard database and an outputs directory.
    Matches the fixture expected by end-to-end studio tests.
    """
    db_path = os.path.join(temp_dir, "test_blackboard.db")
    output_dir = os.path.join(temp_dir, "outputs")
    os.makedirs(output_dir, exist_ok=True)

    init_db(db_path)

    yield {
        "db_path": db_path,
        "output_dir": output_dir,
    }


@pytest.fixture
def sample_campaign_data() -> Dict[str, str]:
    """Standardized marketing brief payload for test campaigns."""
    return {
        "product_name": "Hearth & Crumb Bakery",
        "target_audience": "Neighborhood food lovers and busy families who value organic sourdough",
        "primary_goal": "Offer handcrafted quality and an experience that feels special and elevated.",
        "main_button": "Order Today's Bake",
        "brand_notes": "Warm neutral palette, welcoming and approachable tone, zero corporate fluff.",
    }


@pytest.fixture
def sample_design_system() -> Dict[str, Any]:
    """Sample design token payload matching the Orchestrator schema."""
    return {
        "theme_name": "Warm Rustic Editorial",
        "primary_color": "#D97706",
        "secondary_color": "#78350F",
        "background_color": "#F7F6F2",
        "text_color": "#2D312E",
        "font_family": "system-ui, -apple-system, sans-serif",
        "border_radius": "8px",
    }


@pytest.fixture
def sample_copy_brief() -> Dict[str, Any]:
    """Sample copy brief payload matching the Orchestrator schema."""
    return {
        "hero_headline": "Artisan Sourdough, Baked Fresh Every Morning",
        "hero_subheadline": "Slow-fermented organic breads crafted by hand for pure flavor and simple digestion.",
        "primary_cta": "Reserve Your Loaf",
        "value_props": [
            "100% Organic Heritage Flours",
            "36-Hour Natural Fermentation",
            "Delivered Fresh to Your Doorstep",
        ],
        "social_proof": "Voted Best Neighborhood Bakery 2026",
    }


@pytest.fixture
def seeded_campaign(
    temp_db: str,
    sample_campaign_data: Dict[str, str],
    sample_design_system: Dict[str, Any],
    sample_copy_brief: Dict[str, Any],
) -> Dict[str, Any]:
    """Seeds a complete campaign with 5 framework tasks directly into the SQLite blackboard without calling LLMs."""
    campaign_id = "camp_test_fixture_101"
    create_campaign(
        campaign_id=campaign_id,
        product_name=sample_campaign_data["product_name"],
        target_audience=sample_campaign_data["target_audience"],
        primary_goal=sample_campaign_data["primary_goal"],
        brand_notes=sample_campaign_data["brand_notes"],
        db_path=temp_db,
    )

    frameworks = ["mastra", "strands", "google", "crewai", "langgraph"]
    archetypes = [
        "Editorial Storyteller",
        "Conversion Driver",
        "Social Proof Heavy",
        "Minimalist Showcase",
        "Feature Grid Bento",
    ]

    task_ids = []
    for framework, archetype in zip(frameworks, archetypes):
        task_id = insert_task(
            campaign_id=campaign_id,
            archetype=archetype,
            framework=framework,
            design_system=sample_design_system,
            copy_brief=sample_copy_brief,
            db_path=temp_db,
        )
        task_ids.append(task_id)

    return {
        "campaign_id": campaign_id,
        "db_path": temp_db,
        "task_ids": task_ids,
        "frameworks": frameworks,
    }