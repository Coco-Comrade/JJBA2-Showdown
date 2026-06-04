"""Launch JJBA2: The Showdown from the project root."""

from jjba2.app import main
from jjba2.config import logger


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Fatal game crash")
        raise
