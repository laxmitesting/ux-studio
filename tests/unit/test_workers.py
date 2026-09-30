import os
import pytest
from db.database import init_db, create_campaign, insert_task, get_campaign_tasks
from workers.base_worker import BaseWorker, build_worker_prompt

SAMPLE_VALID_HTML = (
    "<!DOCTYPE html>\n"
    "<html lang=\"en\">\n"
    "<head>\n"
    "    <meta charset=\"UTF-8\">\n"
    "    <title>High Speed Experience</title>\n"
    "    <style>\n"
    "        :root { --bg: #ffffff; --text: #111111; --brand: #2563EB; }\n"
    "        body { font-family: sans-serif; background: var(--bg); color: var(--text); padding: 2rem; }\n"
    "    </style>\n"
    "</head>\n"
    "<body>\n"
    "    <header><h1>Ship in Minutes</h1></header>\n"
    "    <main><p>Instant zero-friction builds designed for modern engineers and production scale.</p></main>\n"
    "</body>\n"
    "</html>"
)


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_workers.db")
    init_db(db_file)
    return db_file


@pytest.fixture
def temp_output_dir(tmp_path):
    out_dir = tmp_path / "outputs"
    out_dir.mkdir()
    return str(out_dir)


class DummyTestWorker(BaseWorker):
    def __init__(self, db_path, output_dir, return_content=SAMPLE_VALID_HTML):
        super().__init__(framework_name="dummy", db_path=db_path, output_dir=output_dir)
        self.return_content = return_content
        self.generate_called = False

    def generate_page(self, prompt: str, task_data: dict) -> str:
        self.generate_called = True
        return self.return_content


def test_build_worker_prompt():
    task_data = {
        "angle": "High Speed",
        "target_persona": "Busy Devs",
        "design_system": {
            "brand_color": "#2563EB",
            "canvas_theme": "dark",
            "cta_color": "#10B981",
            "typography_mood": "modern sans-serif",
            "layout_hierarchy": "bento grid",
        },
        "copy_brief": {
            "hero_headline": "Ship in Minutes",
            "subheadline": "Zero-friction builds",
            "key_benefits": ["Instant caching", "One-click deployment"],
            "cta_label": "Deploy Now",
        },
    }
    prompt = build_worker_prompt(task_data)
    assert "High Speed" in prompt
    assert "#2563EB" in prompt
    assert "Deploy Now" in prompt


def test_worker_end_to_end_flow(temp_db, temp_output_dir):
    create_campaign(
        campaign_id="camp_test",
        product_name="Test Product",
        target_audience="Developers",
        primary_goal="Signups",
        db_path=temp_db,
    )

    insert_task(
        campaign_id="camp_test",
        archetype="High Speed",
        framework="dummy",
        design_system={
            "brand_color": "#000000",
            "canvas_theme": "light",
            "cta_color": "#FF0000",
            "typography_mood": "sans",
            "layout_hierarchy": "grid",
        },
        copy_brief={
            "hero_headline": "Headline",
            "subheadline": "Sub",
            "key_benefits": ["B1"],
            "cta_label": "Go",
        },
        db_path=temp_db,
    )

    worker = DummyTestWorker(db_path=temp_db, output_dir=temp_output_dir, return_content=SAMPLE_VALID_HTML)
    processed = worker.run_once()

    assert processed is True
    assert worker.generate_called is True

    tasks = get_campaign_tasks("camp_test", db_path=temp_db)
    assert len(tasks) == 1
    assert tasks[0]["status"] == "completed"
    assert os.path.exists(tasks[0]["output_html_path"])

    with open(tasks[0]["output_html_path"], "r", encoding="utf-8") as f:
        saved_content = f.read()
    assert "Ship in Minutes" in saved_content
    assert "Generation Failed" not in saved_content


def test_worker_fallback_on_invalid_output(temp_db, temp_output_dir):
    create_campaign(
        campaign_id="camp_test",
        product_name="Test Product",
        target_audience="Developers",
        primary_goal="Signups",
        db_path=temp_db,
    )

    insert_task(
        campaign_id="camp_test",
        archetype="High Speed",
        framework="dummy",
        design_system={
            "brand_color": "#000000",
            "canvas_theme": "light",
            "cta_color": "#FF0000",
            "typography_mood": "sans",
            "layout_hierarchy": "grid",
        },
        copy_brief={
            "hero_headline": "Headline",
            "subheadline": "Sub",
            "key_benefits": ["B1"],
            "cta_label": "Go",
        },
        db_path=temp_db,
    )

    # Worker returning invalid output
    worker = DummyTestWorker(db_path=temp_db, output_dir=temp_output_dir, return_content="invalid snippet")
    processed = worker.run_once()

    assert processed is True
    tasks = get_campaign_tasks("camp_test", db_path=temp_db)
    assert tasks[0]["status"] == "completed"
    assert os.path.exists(tasks[0]["output_html_path"])

    with open(tasks[0]["output_html_path"], "r", encoding="utf-8") as f:
        saved_content = f.read()
    assert "Generation Failed" in saved_content
    assert "High Speed" in saved_content