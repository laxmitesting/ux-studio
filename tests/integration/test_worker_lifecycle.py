import os
import time
import threading
import pytest
from db.database import (
    init_db,
    create_campaign,
    insert_task,
    get_campaign_tasks,
)
from workers.base_worker import BaseWorker

SAMPLE_VALID_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Integration Test Variant</title>
    <style>body { font-family: sans-serif; background: #fff; color: #111; }</style>
</head>
<body>
    <header><h1>Autonomous Generation</h1></header>
    <main><p>Verified Blackboard Pipeline Execution with adequate byte size.</p></main>
</body>
</html>"""


class MockFrameworkWorker(BaseWorker):
    """Simulates a framework worker without live external LLM network latency."""
    def __init__(self, framework_name: str, db_path: str, output_dir: str):
        super().__init__(
            framework_name=framework_name,
            db_path=db_path,
            output_dir=output_dir,
            poll_interval=0.1,  # Fast polling for test speed
        )

    def generate_page(self, prompt: str, task_data: dict) -> str:
        # Slight simulated compute delay to test race condition handling
        time.sleep(0.05)
        return SAMPLE_VALID_HTML


@pytest.fixture
def integration_env(tmp_path):
    db_file = str(tmp_path / "lifecycle_blackboard.db")
    output_dir = str(tmp_path / "outputs")
    init_db(db_file)
    return {"db_path": db_file, "output_dir": output_dir}


def test_concurrent_worker_lifecycle(integration_env):
    db_path = integration_env["db_path"]
    output_dir = integration_env["output_dir"]
    campaign_id = "camp_lifecycle_concurrency"

    # 1. Create campaign
    create_campaign(
        campaign_id=campaign_id,
        product_name="Concurrency Engine",
        target_audience="DevOps Leads",
        primary_goal="Validate Multi-Worker Execution",
        db_path=db_path,
    )

    frameworks = ["agno", "google_adk", "maf", "mastra", "strands"]

    # 2. Seed 5 tasks into blackboard
    for idx, fw in enumerate(frameworks):
        insert_task(
            campaign_id=campaign_id,
            archetype=f"Archetype_{fw.upper()}",
            framework=fw,
            design_system={
                "brand_color": "#4F46E5",
                "canvas_theme": "dark",
                "cta_color": "#10B981",
                "typography_mood": "modern sans",
                "layout_hierarchy": "bento grid",
            },
            copy_brief={
                "hero_headline": f"Scalable {fw.title()}",
                "subheadline": "Enterprise speed at scale",
                "key_benefits": ["High concurrency", "Resilient fallback"],
                "cta_label": "Start Now",
            },
            db_path=db_path,
        )

    # 3. Spin up 5 concurrent workers on separate threads
    workers = [
        MockFrameworkWorker(framework_name=fw, db_path=db_path, output_dir=output_dir)
        for fw in frameworks
    ]

    threads = []
    for w in workers:
        t = threading.Thread(target=w.start_polling, daemon=True)
        threads.append(t)
        t.start()

    # 4. Wait for completion (max 10s timeout)
    timeout = 10.0
    start_time = time.time()
    completed = False

    while time.time() - start_time < timeout:
        tasks = get_campaign_tasks(campaign_id=campaign_id, db_path=db_path)
        statuses = [t["status"] for t in tasks]
        if len(statuses) == len(frameworks) and all(s == "completed" for s in statuses):
            completed = True
            break
        time.sleep(0.2)

    # 5. Stop all workers
    for w in workers:
        w.stop_polling()

    for t in threads:
        t.join(timeout=1.0)

    # 6. Verify assertions
    assert completed is True, f"Workers did not complete all tasks in time. Statuses: {statuses}"

    final_tasks = get_campaign_tasks(campaign_id=campaign_id, db_path=db_path)
    assert len(final_tasks) == 5

    for task in final_tasks:
        assert task["status"] == "completed"
        assert task["output_html_path"] is not None
        assert os.path.exists(task["output_html_path"])
        with open(task["output_html_path"], "r", encoding="utf-8") as f:
            content = f.read()
        assert "Verified Blackboard Pipeline Execution" in content