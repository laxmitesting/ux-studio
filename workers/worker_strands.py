import os
import logging
from typing import Dict, Any, Optional

from workers.base_worker import BaseWorker
from db.database import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)

from strands import Agent
from strands.models.openai import OpenAIModel

class StrandsWorker(BaseWorker):
    """Worker powered by the Strands agent framework."""

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        model_id: str = "gpt-5.4-mini",
        api_key: Optional[str] = None,
        poll_interval: float = 2.0,
    ):
        super().__init__(framework_name="strands", db_path=db_path, poll_interval=poll_interval)
        
        # Ensure OPENAI_API_KEY is available in the environment for the client
        key = api_key or os.getenv("OPENAI_API_KEY")
        if key:
            os.environ["OPENAI_API_KEY"] = key
            
        self.model_id = model_id

        # Pass 'model_id' instead of 'model', omit 'api_key'
        model = OpenAIModel(model_id=self.model_id)

        self.agent = Agent(
            model=model,
            system_prompt=(
                "You are an expert Frontend Architect and UX Engineer. "
                "Your objective is to generate semantic, responsive, production-ready single-file HTML pages."
            ),
        )

    def generate_page(self, prompt: str, task_data: Dict[str, Any]) -> str:
        """Executes agent generation."""
        # Depending on whether your version uses agent.run() or direct call:
        if hasattr(self.agent, "run"):
            response = self.agent.run(prompt)
        else:
            response = self.agent(prompt)

        if hasattr(response, "content"):
            return str(response.content)
        if hasattr(response, "text"):
            return str(response.text)
        return str(response)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    worker = StrandsWorker()
    worker.start_polling()