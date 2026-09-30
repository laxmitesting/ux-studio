import os
import signal
import sys
import threading
import time
from typing import List

from dotenv import load_dotenv

load_dotenv(override=True)

from db.database import init_db, DEFAULT_DB_PATH
from workers.base_worker import BaseWorker

try:
    from utils.logger import setup_logger
    logger = setup_logger("StudioRunner")
except ImportError:
    import logging
    logger = logging.getLogger("StudioRunner")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-7s | [%(name)s] %(message)s"
        )


def get_available_workers(db_path: str = DEFAULT_DB_PATH) -> List[BaseWorker]:
    """Dynamically loads and instantiates all available framework workers."""
    workers: List[BaseWorker] = []

    # 1. Agno
    try:
        from workers.worker_agno import AgnoWorker
        workers.append(AgnoWorker(db_path=db_path))
        logger.info("Loaded worker: Agno")
    except Exception as e:
        logger.warning(f"Could not load AgnoWorker: {e}")

    # 2. Google ADK
    try:
        from workers.worker_google_adk import GoogleADKWorker
        workers.append(GoogleADKWorker(db_path=db_path))
        logger.info("Loaded worker: Google ADK")
    except Exception as e:
        logger.warning(f"Could not load GoogleADKWorker: {e}")

    # 3. Microsoft AutoGen Framework (MAF)
    try:
        from workers.worker_maf import MAFWorker
        workers.append(MAFWorker(db_path=db_path))
        logger.info("Loaded worker: MAF")
    except Exception as e:
        logger.warning(f"Could not load MAFWorker: {e}")

    # 4. Mastra
    try:
        from workers.worker_mastra import MastraWorker
        workers.append(MastraWorker(db_path=db_path))
        logger.info("Loaded worker: Mastra")
    except Exception as e:
        logger.warning(f"Could not load MastraWorker: {e}")

    # 5. Strands
    try:
        from workers.worker_strands import StrandsWorker
        workers.append(StrandsWorker(db_path=db_path))
        logger.info("Loaded worker: Strands")
    except Exception as e:
        logger.warning(f"Could not load StrandsWorker: {e}")

    return workers


def main():
    init_db(DEFAULT_DB_PATH)

    workers = get_available_workers(DEFAULT_DB_PATH)
    if not workers:
        logger.error("No workers could be loaded. Please check dependencies and worker files.")
        sys.exit(1)

    threads: List[threading.Thread] = []

    def shutdown_signal_handler(sig, frame):
        logger.info("Shutdown signal received. Stopping worker threads...")
        for w in workers:
            w.stop_polling()
        for t in threads:
            t.join(timeout=2.0)
        logger.info("All workers cleanly stopped. Exiting.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_signal_handler)
    signal.signal(signal.SIGTERM, shutdown_signal_handler)

    logger.info(f"Starting {len(workers)} worker threads for database: {DEFAULT_DB_PATH}")

    for w in workers:
        t = threading.Thread(
            target=w.start_polling,
            name=f"Thread-{w.framework_name}",
            daemon=True
        )
        threads.append(t)
        t.start()

    logger.info("UX Studio Runner is live. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown_signal_handler(None, None)


if __name__ == "__main__":
    main()