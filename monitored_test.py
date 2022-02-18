from datetime import datetime, timedelta
import os
import logging
import random

import click

from tg_shill_bot.model import *

from tg_shill_bot.data_sources.reddit import RedditDataSource
from tg_shill_bot.data_sources.twitter import TwitterDataSource

from tg_shill_bot import create_session
from tg_shill_bot.tg_shill_bot import ShillBot

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--telegram-token", envvar="TELEGRAM_TOKEN", help="Telegram bot token")
@click.option("--database", envvar="DATABASE_URL", help="Database connection string")
@click.option("--twitter-api-key", envvar="TWITTER_API_KEY", help="Twitter API key")
@click.option(
    "--twitter-api-key-secret",
    envvar="TWITTER_API_KEY_SECRET",
    help="Twitter API key secret",
)
@click.option(
    "--twitter-bearer-token", envvar="TWITTER_BEARER_TOKEN", help="Twitter bearer token"
)
def cli(
    telegram_token: str,
    database: str,
    twitter_api_key: str,
    twitter_api_key_secret: str,
    twitter_bearer_token: str,
) -> None:
    logger.info("Starting Telegram Shill Bot")
    session = create_session(database="sqlite:///tg_shill_bot.db")
    logger.info("Created DB session")

    logger.info("Running monitoring test...")

    start_time = datetime.utcnow() - timedelta(hours=1)

    chats = session.query(ChatRoom).all()
    for chat in chats:
        twitter_ds = TwitterDataSource(
            api_key=twitter_api_key,
            api_key_secret=twitter_api_key_secret,
            bearer_token=twitter_bearer_token,
        )

        twitter_feeds = (
            session.query(LinkTracker)
            .filter(
                LinkTracker.chat_id == chat.chat_id,
                LinkTracker.created_at > start_time,
                LinkTracker.link_type == "twitter",
            )
            .order_by(LinkTracker.created_at.desc())
            .all()
        )

        for feed in twitter_feeds:
            twitter_ds.check_engagement(tweet_url=feed.link, tags=chat.tags.split(" "))


if __name__ == "__main__":
    cli(auto_envvar_prefix="TSB")
