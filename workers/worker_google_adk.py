import os
import logging
from typing import Dict, Any, Optional

from google import genai
from google.genai import types

from workers.base_worker import BaseWorker
from db.database import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


class GoogleADKWorker(BaseWorker):
    """Worker powered by Google GenAI / ADK."""

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        model_id: str = "gemini-3.8-flash",
        api_key: Optional[str] = None,
        poll_interval: float = 2.0,
    ):
        super().__init__(framework_name="google_adk", db_path=db_path, poll_interval=poll_interval)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_id = model_id
        
        # Initialize Google GenAI client
        self.client = genai.Client(api_key=self.api_key)

    def generate_page(self, prompt: str, task_data: Dict[str, Any]) -> str:
        """Invokes Gemini via the GenAI SDK to generate single-file HTML."""
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are an expert Frontend Architect. Return only valid HTML markup.",
                temperature=0.7,
            ),
        )
        return response.text or ""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    worker = GoogleADKWorker()
    worker.start_polling()