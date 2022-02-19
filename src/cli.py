#!/usr/bin/env python3

import os
import logging

import click

from tg_shill_bot import create_session
from tg_shill_bot.tg_shill_bot import ShillBot

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command(help="Telegram bot for monitoring social feeds for shill opportunities")
@click.option("--telegram-token", envvar="TELEGRAM_TOKEN", help="Telegram bot token")
@click.option("--database", envvar="DATABASE_URL", help="Database connection string")
def cli(telegram_token: str, database: str) -> None:
    logger.info("Starting Telegram Shill Bot")
    session = create_session(database=database)

    logger.info("Created DB session")

    bot = ShillBot(db_session=session, telegram_token=telegram_token)

    logger.info("Finished Telegram Shill Bot")


if __name__ == "__main__":
    cli(auto_envvar_prefix="TSB")
