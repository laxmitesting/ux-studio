import os
import logging

from typing import Dict, Any, Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from workers.base_worker import BaseWorker
from db.database import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


class AgnoWorker(BaseWorker):
    """Worker powered by the Agno agent framework."""

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        model_id: str = "gpt-5.4-mini",
        api_key: Optional[str] = None,
        poll_interval: float = 2.0,
    ):
        super().__init__(framework_name="agno", db_path=db_path, poll_interval=poll_interval)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_id = model_id
        
        # Initialize the Agno Agent
        self.agent = Agent(
            model=OpenAIChat(id=self.model_id, api_key=self.api_key),
            markdown=False,
            description="You are a senior frontend developer specializing in building clean, responsive landing pages.",
        )

    def generate_page(self, prompt: str, task_data: Dict[str, Any]) -> str:
        """Invokes the Agno agent to generate single-file HTML."""
        response = self.agent.run(prompt)
        # Agno responses expose content via .content
        return getattr(response, "content", str(response))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    worker = AgnoWorker()
    worker.start_polling()