import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

# Initialize logger safely
try:
    from utils.logger import setup_logger
    logger = setup_logger("database")
except ImportError:
    import logging
    logger = logging.getLogger("database")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | [%(name)s] %(message)s")

DEFAULT_DB_PATH = os.getenv("BLACKBOARD_DB_PATH", "data/blackboard.db")


@contextmanager
def get_connection(db_path: str = DEFAULT_DB_PATH):
    """Context manager for SQLite connections with WAL mode and row factory."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes tables and indexes."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                target_audience TEXT NOT NULL,
                primary_goal TEXT NOT NULL,
                brand_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                archetype TEXT NOT NULL,
                framework TEXT NOT NULL,
                design_system TEXT NOT NULL,
                copy_brief TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                output_html_path TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
            );
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_claim ON tasks (status, framework, created_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_campaign ON tasks (campaign_id);")


def create_campaign(
    campaign_id: str,
    product_name: str,
    target_audience: str,
    primary_goal: str,
    brand_notes: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO campaigns (id, product_name, target_audience, primary_goal, brand_notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (campaign_id, product_name, target_audience, primary_goal, brand_notes or "")
        )


def insert_task(
    campaign_id: str,
    archetype: str,
    framework: str,
    design_system: Dict[str, Any],
    copy_brief: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (campaign_id, archetype, framework, design_system, copy_brief, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (
                campaign_id,
                archetype,
                framework.lower(),
                json.dumps(design_system) if isinstance(design_system, dict) else str(design_system),
                json.dumps(copy_brief) if isinstance(copy_brief, dict) else str(copy_brief)
            )
        )
        return cursor.lastrowid


def claim_next_task(
    framework: Optional[str] = None,
    worker_id: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> Optional[Dict[str, Any]]:
    """Claims next pending task. If framework is None, claims next task for any framework."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if framework:
            cursor.execute(
                """
                SELECT id, campaign_id, archetype, framework, design_system, copy_brief
                FROM tasks
                WHERE status = 'pending' AND framework = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (framework.lower(),)
            )
        else:
            cursor.execute(
                """
                SELECT id, campaign_id, archetype, framework, design_system, copy_brief
                FROM tasks
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                """
            )
        row = cursor.fetchone()
        if not row:
            return None
        
        task_id = row["id"]
        cursor.execute(
            """
            UPDATE tasks
            SET status = 'claimed', updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'pending'
            """,
            (task_id,)
        )
        if cursor.rowcount == 0:
            return None
            
        task_dict = {
            "id": row["id"],
            "campaign_id": row["campaign_id"],
            "angle": row["archetype"],
            "archetype": row["archetype"],
            "framework": row["framework"],
            "design_system": json.loads(row["design_system"]) if isinstance(row["design_system"], str) else row["design_system"],
            "copy_brief": json.loads(row["copy_brief"]) if isinstance(row["copy_brief"], str) else row["copy_brief"]
        }
        if worker_id:
            task_dict["worker_id"] = worker_id
        return task_dict


def mark_task_completed(task_id: int, output_html_path: str, db_path: str = DEFAULT_DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'completed', output_html_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (output_html_path, task_id)
        )


def mark_task_failed(task_id: int, error_message: str, db_path: str = DEFAULT_DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'failed', error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (error_message, task_id)
        )


def get_campaign_tasks(campaign_id: str, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT id, archetype, framework, status, output_html_path, error_message, updated_at
            FROM tasks
            WHERE campaign_id = ?
            ORDER BY id ASC
            """,
            (campaign_id,)
        )
        return [dict(row) for row in cursor.fetchall()]