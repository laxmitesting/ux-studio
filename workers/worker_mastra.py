import os
import subprocess
import logging
from typing import Dict, Any, Optional

from workers.base_worker import BaseWorker
from db.database import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


class MastraWorker(BaseWorker):
    """Worker powered by Mastra via Node.js subprocess bridge."""

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        api_key: Optional[str] = None,
        poll_interval: float = 2.0,
        script_path: Optional[str] = None,
    ):
        super().__init__(framework_name="mastra", db_path=db_path, poll_interval=poll_interval)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.script_path = script_path or os.path.join(
            os.path.dirname(__file__), "mastra_agent.js"
        )

    def generate_page(self, prompt: str, task_data: Dict[str, Any]) -> str:
        """Pipes the prompt through Node.js stdin and captures the generated HTML."""
        env = os.environ.copy()
        if self.api_key:
            env["OPENAI_API_KEY"] = self.api_key

        process = subprocess.run(
            ["node", self.script_path],
            input=prompt,
            text=True,
            capture_output=True,
            env=env,
            timeout=120,
        )

        if process.returncode != 0:
            raise RuntimeError(f"Mastra agent failed: {process.stderr.strip()}")

        return process.stdout.strip()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    worker = MastraWorker()
    worker.start_polling()