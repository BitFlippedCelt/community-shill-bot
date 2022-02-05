from typing import Union
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


def create_session(
    database: str,
) -> Union[any, None]:
    logger.info(f"Creating session for {database}")

    connection_string = f"{database}"
    try:
        engine = create_engine(connection_string)

        return sessionmaker(engine)()

    except Exception as exc:
        logger.error(f"Could not create DB session for {database} : {exc}")

    return None
