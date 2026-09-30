import pytest
import os
from db.database import (
    init_db,
    create_campaign,
    insert_task,
    claim_next_task,
    mark_task_completed,
    mark_task_failed,
    get_campaign_tasks
)

@pytest.fixture
def temp_db(tmp_path):
    """Provides a fresh, temporary SQLite database path for testing."""
    db_file = str(tmp_path / "test_blackboard.db")
    init_db(db_file)
    return db_file

def test_campaign_and_task_lifecycle(temp_db):
    # 1. Create Campaign
    create_campaign(
        campaign_id="camp_123",
        product_name="DTC Espresso",
        target_audience="Coffee geeks",
        primary_goal="Pre-order",
        db_path=temp_db
    )
    
    # 2. Insert Task
    task_id = insert_task(
        campaign_id="camp_123",
        archetype="minimalist",
        framework="agno",
        design_system={"palette": ["#000000", "#FFFFFF"]},
        copy_brief={"headline": "Pure Coffee."},
        db_path=temp_db
    )
    assert task_id == 1

# 3. Claim Task
    claimed = claim_next_task(worker_id="worker_1", db_path=temp_db)
    assert claimed is not None
    assert claimed["id"] == 1
    assert claimed["angle"] == "minimalist"
    assert claimed["design_system"]["palette"] == ["#000000", "#FFFFFF"]

    # 4. Immediate second claim should return None (no more pending tasks)
    second_claim = claim_next_task(worker_id="worker_2", db_path=temp_db)
    assert second_claim is None

    # 5. Mark Completed
    mark_task_completed(task_id=1, output_html_path="outputs/variant_min.html", db_path=temp_db)
    
    # 6. Verify Dashboard Query
    tasks = get_campaign_tasks(campaign_id="camp_123", db_path=temp_db)
    assert len(tasks) == 1
    assert tasks[0]["status"] == "completed"
    assert tasks[0]["output_html_path"] == "outputs/variant_min.html"