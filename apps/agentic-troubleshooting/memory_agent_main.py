"""Memory Agent entry point."""

import logging
import sys
from src.agents.memory_agent_server import main as memory_main
from src.config.settings import Config

# Simple logging setup
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("Starting Memory Agent A2A Server...")
        memory_main()
    except Exception as e:
        logger.error(f"Memory Agent startup error: {e}")
        sys.exit(1)
