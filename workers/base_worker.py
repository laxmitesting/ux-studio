import os
import sys
import time
import json
import sqlite3
import traceback
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db.database import DEFAULT_DB_PATH

# Centralized logger
try:
    from utils.logger import setup_logger
    logger = setup_logger("worker")
except ImportError:
    import logging
    logger = logging.getLogger("worker")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-7s | [%(name)s] %(message)s"
        )


def build_worker_prompt(task: Dict[str, Any]) -> str:
    """
    Constructs the standardized prompt for workers from task dictionary data.
    """
    angle = task.get("angle") or task.get("archetype", "Landing Page")
    persona = task.get("target_persona", "General Audience")
    design_system = task.get("design_system", {})
    copy_brief = task.get("copy_brief", {})

    if isinstance(design_system, str):
        try:
            design_system = json.loads(design_system)
        except Exception:
            pass

    if isinstance(copy_brief, str):
        try:
            copy_brief = json.loads(copy_brief)
        except Exception:
            pass

    benefits = copy_brief.get("key_benefits") or copy_brief.get("value_props", [])
    if isinstance(benefits, list):
        benefits_str = "\n".join(f"- {b}" for b in benefits)
    else:
        benefits_str = str(benefits)

    return f"""
Angle / Theme: {angle}
Target Persona: {persona}

Design System:
{json.dumps(design_system, indent=2) if isinstance(design_system, dict) else design_system}

Copy Brief & Content:
Headline: {copy_brief.get('hero_headline', '')}
Subheadline: {copy_brief.get('subheadline', copy_brief.get('hero_subheadline', ''))}
CTA Label: {copy_brief.get('cta_label', copy_brief.get('primary_cta', 'Get Started'))}
Key Benefits:
{benefits_str}
""".strip()


def generate_fallback_html(task: Dict[str, Any], reason: str = "Invalid output") -> str:
    """Generates a graceful fallback HTML page containing 'Generation Failed'."""
    angle = task.get("angle") or task.get("archetype", "Variant")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Generation Failed - {angle}</title>
</head>
<body>
    <h1>Generation Failed</h1>
    <p>Worker failed to produce valid HTML for angle: {angle}</p>
</body>
</html>"""


class BaseWorker(ABC):
    """
    Abstract base worker handling SQLite blackboard polling, task claiming,
    lifecycle timing, file writing, status transitions, and centralized logging.
    """

    def __init__(
        self,
        framework_name: Optional[str] = None,
        framework: Optional[str] = None,
        db_path: str = DEFAULT_DB_PATH,
        output_dir: str = "outputs",
        poll_interval: float = 2.0,
    ):
        name = framework_name or framework or "generic"
        self.framework = name.lower()
        self.framework_name = name
        self.db_path = db_path
        self.output_dir = output_dir
        self.poll_interval = poll_interval
        self._running = False
        os.makedirs(self.output_dir, exist_ok=True)

    @abstractmethod
    def generate_page(self, prompt: str, task_data: dict) -> str:
        """Subclasses implement framework-specific synthesis and return pure HTML."""
        pass

    def claim_task(self, worker_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Atomically finds and claims the oldest pending task for this framework."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT * FROM tasks
                WHERE framework = ? AND status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (self.framework,)
            )
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None

            task = dict(row)
            task_id = task["id"]

            cursor.execute(
                """
                UPDATE tasks
                SET status = 'claimed', updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
                """,
                (task_id,)
            )
            conn.commit()

            if cursor.rowcount == 0:
                conn.close()
                return None

            conn.close()

            # Deserialize JSON payloads
            for json_field in ("design_system", "copy_brief"):
                if isinstance(task.get(json_field), str):
                    try:
                        task[json_field] = json.loads(task[json_field])
                    except (json.JSONDecodeError, TypeError):
                        pass

            # Provide both 'angle' and 'archetype'
            if "archetype" in task and "angle" not in task:
                task["angle"] = task["archetype"]
            if "angle" in task and "archetype" not in task:
                task["archetype"] = task["angle"]

            if worker_id:
                task["worker_id"] = worker_id

            logger.info(
                f"[{self.framework.upper()}] Claimed task #{task_id} "
                f"(Campaign: {task.get('campaign_id')}, Angle: '{task.get('angle', '')}')"
            )
            return task

        except Exception as e:
            conn.close()
            logger.error(f"[{self.framework.upper()}] Database error while claiming task: {e}")
            return None

    def mark_completed(self, task_id: int, output_html_path: str, duration_sec: float) -> None:
        """Updates task to completed with output path in the blackboard."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE tasks
            SET status = 'completed', output_html_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (output_html_path, task_id)
        )
        conn.commit()
        conn.close()
        logger.info(
            f"[{self.framework.upper()}] Task #{task_id} COMPLETED in {duration_sec:.2f}s "
            f"-> Saved: {output_html_path}"
        )

    def mark_failed(self, task_id: int, error_message: str) -> None:
        """Updates task to failed with error message in the blackboard."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE tasks
            SET status = 'failed', error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (error_message, task_id)
        )
        conn.commit()
        conn.close()
        logger.error(f"[{self.framework.upper()}] Task #{task_id} FAILED: {error_message}")

    def run_once(self) -> bool:
        """
        Executes one task lifecycle: claim -> generate -> save -> complete/fail.
        """
        task = self.claim_task()
        if not task:
            return False

        task_id = task["id"]
        campaign_id = task.get("campaign_id", "default_camp")
        archetype = task.get("angle") or task.get("archetype", "landing_page")

        logger.info(f"[{self.framework.upper()}] Synthesizing landing page for '{archetype}'...")
        start_time = time.perf_counter()

        try:
            prompt = build_worker_prompt(task)
            
            # Subclass generates content
            html_content = self.generate_page(prompt, task)

            clean_html = str(html_content).strip() if html_content else ""

            # 1. Strip markdown fences if wrapped in ```html ... ```
            if clean_html.startswith("```"):
                lines = clean_html.splitlines()
                first_line = lines[0].lower()
                if "html" in first_line or first_line == "```":
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                clean_html = "\n".join(lines).strip()

            lower_html = clean_html.lower()

            # 2. Case-insensitive and lenient check for basic HTML structure
            is_valid_html = (
                ("<html" in lower_html and ("</html>" in lower_html or "</body" in lower_html)) or
                ("<!doctype html" in lower_html and "</" in lower_html)
            )

            if not clean_html or not is_valid_html:
                logger.warning(
                    f"[{self.framework.upper()}] Output failed HTML validation. "
                    f"Sample: {clean_html[:120]!r}... Falling back."
                )
                clean_html = generate_fallback_html(task, reason="Invalid HTML generated")

            safe_archetype = str(archetype).lower().replace(" ", "_").replace("/", "_")
            filename = f"{campaign_id}_{self.framework}_{safe_archetype}.html"
            output_path = os.path.join(self.output_dir, filename)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(clean_html)

            duration = time.perf_counter() - start_time
            self.mark_completed(task_id=task_id, output_html_path=output_path, duration_sec=duration)
            return True

        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(
                f"[{self.framework.upper()}] Uncaught exception on task #{task_id}:\n{traceback.format_exc()}"
            )
            self.mark_failed(task_id=task_id, error_message=err_msg)
            return True

    def start_polling(self) -> None:
        """Continuous polling loop executed by StudioRunner worker threads."""
        self._running = True
        logger.info(f"[{self.framework.upper()}] Polling loop started (Interval: {self.poll_interval}s)")

        while self._running:
            try:
                did_work = self.run_once()
                if not did_work and self._running:
                    time.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"[{self.framework.upper()}] Unexpected loop error: {e}", exc_info=True)
                if self._running:
                    time.sleep(self.poll_interval)

        logger.info(f"[{self.framework.upper()}] Polling loop stopped.")

    def stop_polling(self) -> None:
        """Signals the background polling loop to stop cleanly."""
        self._running = False