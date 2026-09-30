import os
import asyncio
import logging
from typing import Dict, Any, Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo, ModelFamily

from workers.base_worker import BaseWorker
from db.database import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


class MAFWorker(BaseWorker):
    """Worker powered by the Microsoft AutoGen Framework (MAF)."""

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        model_id: str = "gpt-5.4-mini",
        api_key: Optional[str] = None,
        poll_interval: float = 2.0,
    ):
        super().__init__(framework_name="maf", db_path=db_path, poll_interval=poll_interval)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_id = model_id

        # Explicit ModelInfo avoids strict catalog mismatch errors in autogen-ext
        model_info = ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family=ModelFamily.GPT_4O,
        )

        # Initialize AutoGen model client
        self.model_client = OpenAIChatCompletionClient(
            model=self.model_id,
            api_key=self.api_key,
            model_info=model_info,
        )

        self.agent = AssistantAgent(
            name="frontend_architect",
            model_client=self.model_client,
            system_message=(
                "You are an expert Frontend Architect and UX Engineer. "
                "Deliver only raw, standalone HTML5 documents with encapsulated CSS."
            ),
        )

    async def _generate_async(self, prompt: str) -> str:
        """Asynchronous execution loop for AutoGen agent run."""
        response = await self.agent.run(task=prompt)
        if hasattr(response, "messages") and response.messages:
            last_message = response.messages[-1]
            return getattr(last_message, "content", str(last_message))
        return str(response)

    def generate_page(self, prompt: str, task_data: Dict[str, Any]) -> str:
        """Bridges async AutoGen execution to the synchronous BaseWorker loop."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(self._generate_async(prompt))

        return loop.run_until_complete(self._generate_async(prompt))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    worker = MAFWorker()
    worker.start_polling()