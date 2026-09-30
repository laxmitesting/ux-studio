import os
import json
import uuid
import time
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

from db.database import create_campaign, insert_task, DEFAULT_DB_PATH
from orchestrator.prompt_templates import (
    OrchestratorResponse, 
    ORCHESTRATOR_SYSTEM_PROMPT, 
    VALID_FRAMEWORKS
)

# Initialize logger from utils.logger (with safe fallbacks)
try:
    from utils.logger import setup_logger
    logger = setup_logger("orchestrator")
except ImportError:
    try:
        from util.logger import setup_logger
        logger = setup_logger("orchestrator")
    except ImportError:
        import logging
        logger = logging.getLogger("orchestrator")
        if not logger.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s | %(levelname)-7s | [%(name)s] %(message)s"
            )

load_dotenv()

def run_orchestrator(
    product_name: str,
    target_audience: str,
    primary_goal: str,
    brand_notes: Optional[str] = "",
    main_button: Optional[str] = "",
    db_path: str = DEFAULT_DB_PATH,
    client: Optional[OpenAI] = None
) -> str:
    """
    Decomposes a marketing brief into 5 value-prop tasks and commits them to the SQLite blackboard.
    Returns the generated campaign_id.
    """
    campaign_id = f"camp_{uuid.uuid4().hex[:8]}"
    logger.info(f"[{campaign_id}] Initiating synthesis for product: '{product_name}'")
    
    # Enrich the goal description if a main button CTA is provided
    combined_goal = primary_goal
    if main_button and main_button.strip():
        combined_goal = f"{primary_goal.strip()} (Primary CTA Button: '{main_button.strip()}')"
        logger.info(f"[{campaign_id}] Bound primary CTA button: '{main_button.strip()}'")

    # 1. Record the campaign in DB
    try:
        create_campaign(
            campaign_id=campaign_id,
            product_name=product_name,
            target_audience=target_audience,
            primary_goal=combined_goal,
            brand_notes=brand_notes,
            db_path=db_path
        )
        logger.info(f"[{campaign_id}] Campaign record committed to blackboard DB: {db_path}")
    except Exception as e:
        logger.error(f"[{campaign_id}] Failed to record campaign in database: {e}", exc_info=True)
        raise
    
    # 2. Invoke LLM with structured output
    if client is None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "mock-key"))

    button_line = f"Primary CTA Button Label: {main_button}\n" if main_button else ""

    user_prompt = f"""
Product Name: {product_name}
Target Audience: {target_audience}
Customer Promise / Primary Goal: {primary_goal}
{button_line}Additional Brand Notes: {brand_notes}

Generate the 5 distinct angle tasks and assign one to each framework: {', '.join(VALID_FRAMEWORKS)}.
Make sure each angle aligns with this core customer promise and leads visitors naturally toward the primary call to action.
""".strip()

    logger.info(f"[{campaign_id}] Requesting brief decomposition from LLM (gpt-5.4-mini)...")
    start_time = time.perf_counter()

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-5.4-mini",
            messages=[
                {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format=OrchestratorResponse,
        )
        elapsed = time.perf_counter() - start_time
        logger.info(f"[{campaign_id}] LLM response received in {elapsed:.2f}s")
    except Exception as e:
        logger.error(f"[{campaign_id}] Failed LLM structured completion call: {e}", exc_info=True)
        raise
    
    parsed_data: OrchestratorResponse = completion.choices[0].message.parsed
    logger.info(f"[{campaign_id}] Parsed {len(parsed_data.tasks)} framework angle tasks")

    # 3. Insert each angle task into SQLite blackboard
    for task in parsed_data.tasks:
        try:
            task_id = insert_task(
                campaign_id=campaign_id,
                archetype=task.angle_name,
                framework=task.framework,
                design_system=task.design_system.model_dump(),
                copy_brief=task.copy_brief.model_dump(),
                db_path=db_path
            )
            logger.info(
                f"[{campaign_id}] Queued task #{task_id} -> framework: '{task.framework}', archetype: '{task.angle_name}'"
            )
        except Exception as e:
            logger.error(f"[{campaign_id}] Failed to insert task for framework '{task.framework}': {e}", exc_info=True)
            raise

    logger.info(f"[{campaign_id}] All tasks successfully seeded to blackboard. Ready for worker claims.")
    return campaign_id