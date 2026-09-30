import os
import sys
import tempfile
import sqlite3
from pathlib import Path
import pytest

# Ensure project root is in sys.path
CURRENT_FILE = Path(__file__).resolve()
ROOT_DIR = CURRENT_FILE.parent.parent.parent if CURRENT_FILE.parent.name == "e2e" else CURRENT_FILE.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db.database import init_db, get_campaign_tasks
from orchestrator.orchestrator import run_orchestrator
from orchestrator.prompt_templates import VALID_FRAMEWORKS


@pytest.fixture
def temp_env():
    """Sets up an isolated database and outputs directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test_blackboard.db")
        output_dir = os.path.join(tmp_dir, "outputs")
        os.makedirs(output_dir, exist_ok=True)

        # Initialize schema
        init_db(db_path)

        yield {
            "db_path": db_path,
            "output_dir": output_dir,
        }


def _fetch_tasks_as_dicts(db_path: str, campaign_id: str):
    """Directly queries all task columns as dictionaries."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE campaign_id = ? ORDER BY id ASC", (campaign_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def test_orchestrator_seeds_all_framework_tasks(temp_env):
    """
    Verifies that run_orchestrator decomposes a brief and seeds
    exactly one task for each supported framework onto the blackboard.
    """
    db_path = temp_env["db_path"]

    product_name = "CloudPulse Studio"
    target_audience = "Independent coffee shop and boutique retail owners"
    primary_goal = "Save busy people hours each week by handling online ordering"
    main_button = "Start Free Tasting"
    brand_notes = "Warm neutral aesthetic, inviting and friendly tone"

    # 1. Run the orchestrator
    campaign_id = run_orchestrator(
        product_name=product_name,
        target_audience=target_audience,
        primary_goal=primary_goal,
        main_button=main_button,
        brand_notes=brand_notes,
        db_path=db_path,
    )

    assert campaign_id is not None
    assert campaign_id.startswith("camp_")

    # 2. Verify tasks in the blackboard
    tasks = _fetch_tasks_as_dicts(db_path, campaign_id)

    assert len(tasks) == len(VALID_FRAMEWORKS), (
        f"Expected {len(VALID_FRAMEWORKS)} tasks, got {len(tasks)}"
    )

    # Ensure all tasks start in 'pending' status and contain full payload
    assigned_frameworks = set()
    for task in tasks:
        assert task["status"] == "pending"
        assert task["campaign_id"] == campaign_id
        assert task["archetype"] is not None
        assert task["design_system"] is not None
        assert task["copy_brief"] is not None
        assigned_frameworks.add(task["framework"])

    # Verify each framework in VALID_FRAMEWORKS received a task
    for framework in VALID_FRAMEWORKS:
        assert framework in assigned_frameworks, f"Missing task for framework: {framework}"


def test_worker_claim_and_completion_loop(temp_env):
    """
    Simulates a worker claiming a pending task from the blackboard,
    writing HTML output, and marking the task completed.
    """
    db_path = temp_env["db_path"]
    output_dir = temp_env["output_dir"]

    # 1. Seed tasks
    campaign_id = run_orchestrator(
        product_name="Aura Bakery",
        target_audience="Neighborhood families",
        primary_goal="Offer handcrafted quality and an elevated experience",
        main_button="Order Today's Bake",
        db_path=db_path,
    )

    tasks = _fetch_tasks_as_dicts(db_path, campaign_id)
    assert len(tasks) > 0, "No tasks were seeded into the blackboard."

    first_task = tasks[0]
    task_id = first_task["id"]
    framework = first_task["framework"]

    # 2. Simulate task processing
    output_html_file = os.path.join(output_dir, f"{campaign_id}_{framework}.html")
    mock_html_content = "<!DOCTYPE html><html><body><h1>Fresh Daily Sourdough</h1></body></html>"

    with open(output_html_file, "w", encoding="utf-8") as f:
        f.write(mock_html_content)

    # Update blackboard directly (mirrors BaseWorker.complete_task)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE tasks 
        SET status = 'completed', output_html_path = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (output_html_file, task_id),
    )
    conn.commit()
    conn.close()

    # 3. Verify task reflects completion
    updated_tasks = _fetch_tasks_as_dicts(db_path, campaign_id)
    completed_task = next(t for t in updated_tasks if t["id"] == task_id)

    assert completed_task["status"] == "completed"
    assert completed_task["output_html_path"] == output_html_file
    assert os.path.exists(completed_task["output_html_path"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])