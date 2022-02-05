import logging

from tg_shill_bot.bot.telegram import TelegramBot


class ShillBot(object):
    def __init__(self, telegram_token: str, db_session) -> None:
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

        if telegram_token is not None:
            self.telegram_bot = TelegramBot(telegram_token, self.db_session)
