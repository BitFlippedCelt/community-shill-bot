import html
import json
import traceback
from typing import Union

from sqlalchemy.orm import sessionmaker
from tg_shill_bot.bot.common import CommonBot

from tg_shill_bot.data_sources.reddit import RedditDataSource
from tg_shill_bot.data_sources.twitter import TwitterDataSource
from tg_shill_bot.data_sources.youtube import YoutubeDataSource
from tg_shill_bot.model import *

import telegram
from telegram import ParseMode, TelegramError, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

from tg_shill_bot.model import data_source
from tg_shill_bot.model import link_tracker

DEVELOPER_CHAT_ID = "2073823656"
MAX_MESSAGE_LENGTH = 4096


class TelegramBot(CommonBot):
    def __init__(self, db_session: sessionmaker, **kwargs) -> None:
        super().__init__(db_session)

        # Setup Telegram Session
        self.updater = Updater(token=kwargs["token"] if "token" in kwargs else None)
        self.job_queue = self.updater.job_queue
        self.dispatcher = self.updater.dispatcher

        # Add passive monitoring handler
        self.dispatcher.add_handler(
            MessageHandler(
                Filters.status_update.new_chat_members, self.new_chat_members
            )
        )
        self.dispatcher.add_handler(
            MessageHandler(Filters.text & ~Filters.command, self.new_message)
        )

        # Add command handlers
        self.dispatcher.add_handler(CommandHandler("start", self.command_start))
        self.dispatcher.add_handler(CommandHandler("help", self.command_help))
        self.dispatcher.add_handler(
            CommandHandler("list_types", self.command_list_types)
        )
        self.dispatcher.add_handler(
            CommandHandler("list_sources", self.command_list_sources)
        )
        self.dispatcher.add_handler(CommandHandler("links", self.command_list_links))
        self.dispatcher.add_handler(CommandHandler("scrape", self.command_scrape))

        # Add error handler
        self.dispatcher.add_error_handler(self.error_handler)

        # Setup Telegram Background Tasks
        self.job_scrape = self.job_queue.run_repeating(
            self.task_scrape_data, interval=60 * 60, first=60
        )
        self.job_links = self.job_queue.run_repeating(
            self.task_show_recent_links, interval=60 * 15, first=60 * 5
        )
        # self.job_queue.run_repeating(self.check_monitored, interval=60, first=0)

        # Start the Bot
        self.updater.start_polling()
        self.updater.idle()

    def new_chat_members(self, update: Update, context: CallbackContext) -> None:
        """Add a new user to the chat"""
        try:
            chat_room = self.get_chat_room(update)
        except ValueError as e:
            self.logger.error(e)
            return

        for member in update.message.new_chat_members:
            if member.username == CommonBot.BOT_NAME:
                context.bot.send_message(
                    chat_id=chat_room.chat_id,
                    text=f"Thanks for adding me to {update.message.chat.title}, use /start to configure the bot.",
                )
            else:
                context.bot.send_message(
                    chat_id=chat_room.chat_id,
                    text=f"Welcome {member.name}, may the shilling commence!",
                )

    def new_message(self, update: Update, context: CallbackContext) -> None:
        """Handle chat text"""
        try:
            chat_room = self.get_chat_room(update)
        except ValueError as e:
            return

        for link in RedditDataSource.find_links(update.message.text):
            self.store_link(chat_room, link, "reddit")

        for link in TwitterDataSource.find_links(update.message.text):
            self.store_link(chat_room, link, "twitter")

        for link in YoutubeDataSource.find_links(update.message.text):
            self.store_link(chat_room, link, "youtube")

    def command_start(self, update: Update, context: CallbackContext) -> None:
        """Send message on how to use the bot"""
        try:
            self.logger.info(
                f"Start requested for [{update.message.chat.id}] - {update.message.chat.title}"
            )
        except AttributeError:
            pass

        chat_room = self.get_chat_room(update)
        if chat_room is None:
            chat_room = ChatRoom(
                chat_id=update.message.chat_id,
                name=update.message.chat.title
                if update.message.chat.title is not None
                else "Unknown",
                cta_text="SHILL and Grow!",
                scrape_interval=60 * 60,
                update_interval=60 * 15,
            )
            self.db_session.add(chat_room)

            self.db_session.commit()
            self.logger.info(
                f"Added new chat room {chat_room.chat_id} - {update.message.chat.title}"
            )

            update.message.reply_text("Beep boop. Crypto Shill Bot ready for action.")
        else:
            update.message.reply_text("Crypto Shill Bot is already initialized.")

    def command_help(self, update: Update, context: CallbackContext) -> None:
        """Send message with the list of available commands."""
        update.message.reply_text(
            """
/help - Show this message
"""
        )

    def command_list_types(self, update: Update, context: CallbackContext) -> None:
        """List all data source types"""
        try:
            data_source_types = self.list_data_source_types()
            data_source_listing = "\n".join(data_source_types)
            update.message.reply_text(
                f"Available data source types:\n{data_source_listing}"
            )

        except (IndexError, ValueError):
            update.message.reply_text("Usage: /list_types")

    def command_list_sources(self, update: Update, context: CallbackContext) -> None:
        """List all data sources of the given type"""
        try:
            chat_room = self.get_chat_room(update)
        except ValueError as e:
            self.logger.error(e)
            return

        try:
            data_source_type = context.args[0]

            reply_text = ""

            if data_source_type == "twitter":
                reply_text = "🐦🐦 Twitter 🐦🐦\n"
            elif data_source_type == "reddit":
                reply_text = "🤖🤖 Reddit 🤖🤖\n"
            elif data_source_type == "youtube":
                reply_text = "🎥🎥 Youtube 🎥🎥\n"

            data_sources = (
                self.db_session.query(DataSource)
                .filter(
                    DataSource.chat_room_id == chat_room.id,
                    DataSource.data_source_type == data_source_type,
                )
                .all()
            )

            if data_sources is not None:
                for data_source in data_sources:
                    reply_text += f"{data_source.name}, "
            else:
                reply_text += "No datasources found."

            update.message.reply_text(reply_text.rstrip(", "))

        except (IndexError, ValueError):
            update.message.reply_text("Usage: /list_sources <data_source_type>")

    def command_list_links(self, update: Update, context: CallbackContext) -> None:
        """List recently known links"""
        try:
            chat_room = self.get_chat_room(update)
        except ValueError as e:
            self.logger.error(e)
            return

        if chat_room is None:
            update.message.reply_text("This chat room is not initialized. Use /start")
            return

        compact = (
            True if len(context.args) > 0 and context.args[0] == "compact" else False
        )

        self.generate_shill_call_text(
            context=context, chat_room=chat_room, compact=compact
        )

        self.safe_delete_message(
            context=context, chat_room=chat_room, message_id=update.message.message_id
        )

    def command_scrape(self, update: Update, context: CallbackContext) -> None:
        """Maually trigger social scrape"""
        try:
            chat_room = self.get_chat_room(update)
        except ValueError as e:
            self.logger.error(e)
            return

        self.social_scrape(context=context, chat_room=chat_room)

        self.safe_delete_message(
            context=context, chat_room=chat_room, message_id=update.message.message_id
        )

    def error_handler(self, update: Update, context: CallbackContext) -> None:
        """Log the error and send a telegram message to notify the developer."""
        super().error_handler(error=context.error)

        # traceback.format_exception returns the usual python message about an exception, but as a
        # list of strings rather than a single string, so we have to join them together.
        tb_list = traceback.format_exception(
            None, context.error, context.error.__traceback__
        )
        tb_string = "".join(tb_list)

        # Build the message with some markup and additional information about what happened.
        # You might need to add some logic to deal with messages longer than the 4096 character limit.
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f"An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
            "</pre>\n\n"
            f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
            f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
            f"<pre>{html.escape(tb_string)}</pre>"
        )

        try:
            chat_room = (
                self.db_session.query(ChatRoom)
                .filter(ChatRoom.chat_id == DEVELOPER_CHAT_ID)
                .first()
            )

            # Finally, send the message
            self.refresh_tracked_message(
                context=context,
                chat_room=chat_room,
                message=message,
                parse_mode=ParseMode.HTML,
            )
        except ValueError as e:
            self.logger.error(e)

    def task_show_recent_links(self, context: CallbackContext) -> None:
        """Show recent links"""
        self.logger.debug("Sending recent links listing")

        # TODO: Add logic to show recent links per chat room based on configured time period

        chats = self.db_session.query(ChatRoom).all()
        for chat in chats:
            self.logger.debug(
                "Sending recent links listing for chat_id: %s", chat.chat_id
            )

            try:
                self.generate_shill_call_text(context, chat)

            except (IndexError, ValueError):
                self.send_message(
                    context=context, chat_room=chat, message="Usage: /links"
                )

    def task_scrape_data(self, context: CallbackContext) -> None:
        """Scrape data from social media"""
        self.logger.debug("Scraping data")

        # TODO: Add logic to scrape links per chat room based on configured time period

        chats = self.db_session.query(ChatRoom).all()
        for chat in chats:
            self.social_scrape(context=context, chat_room=chat)

    def get_chat_room(self, update: Update) -> ChatRoom:
        """Get the chat room for the update"""
        if update is None:
            raise ValueError("Update is None")
        if update.message is None:
            raise ValueError("Update.Message is None")

        chat_id = update.message.chat_id
        chat_room = super().get_chat_room(chat_id)

        return chat_room

    def social_scrape(self, context: CallbackContext, chat_room: ChatRoom) -> None:
        bot_message = context.bot.send_message(
            chat_id=chat_room.chat_id,
            text="🤖 Beep boop - Please be patient while I check the socials...",
        )

        # message_text = "👇👇 📣📣 SHillcall - New Socials 📣📣 👇👇\n\n"

        posts = self.scrape_reddit_feeds(chat_room=chat_room)
        for post in posts:
            link_tracker = LinkTracker(
                chat_room=chat_room, link=post, link_type="reddit"
            )
            self.db_session.add(link_tracker)

        tweets = self.scrape_twitter_feeds(chat_room=chat_room)
        for tweet in tweets:
            link_tracker = LinkTracker(
                chat_room_id=chat_room.id, link=tweet, link_type="twitter"
            )
            self.db_session.add(link_tracker)

        videos = self.scrape_youtube_feeds(chat_room=chat_room)
        for video in videos:
            link_tracker = LinkTracker(
                chat_room_id=chat_room.id, link=video, link_type="youtube"
            )
            self.db_session.add(link_tracker)

        self.db_session.commit()

        # Remove Beep boop message
        if bot_message is not None:
            self.safe_delete_message(
                context=context, chat_room=chat_room, message_id=bot_message.message_id
            )

    def check_monitored(self, context: CallbackContext) -> None:
        """Check if any monitored data sources have new data"""
        self.logger.debug("Checking monitored data sources")

    def generate_shill_call_text(
        self, context: CallbackContext, chat_room: ChatRoom, compact: bool = False
    ) -> str:
        """Generate the text for the shill call"""
        message = super().generate_shill_call(chat_room=chat_room, compact=compact)

        self.refresh_tracked_message(
            context=context,
            chat_room=chat_room,
            message=message,
            message_type="shill_call_message",
            parse_mode=ParseMode.HTML,
        )

    def send_message(
        self,
        context: CallbackContext,
        chat_room: ChatRoom,
        message: Union[str, list[str]],
        **kwargs,
    ) -> int:
        """Send a message to a chat room"""
        try:
            return context.bot.send_message(
                chat_id=chat_room.chat_id,
                text="".join(message),
                disable_web_page_preview=True,
                **kwargs,
            ).message_id
        except TelegramError as e:
            self.logger.error(e)

    def safe_delete_message(
        self, context: CallbackContext, chat_room: ChatRoom, message_id: int
    ) -> None:
        """Safely delete a message and squash error"""
        try:
            context.bot.delete_message(chat_id=chat_room.chat_id, message_id=message_id)
        except telegram.error.BadRequest:
            self.logger.warning(
                f"Failed to delete message {message_id} in chat {chat_room.chat_id}"
            )

    def refresh_tracked_message(
        self,
        context: CallbackContext,
        chat_room: ChatRoom,
        message: Union[str, list[str]],
        message_type: str = None,
        **kwargs,
    ) -> list[int]:
        """Refresh tracked message"""
        if chat_room.chat_id not in self.message_tracking:
            self.message_tracking[chat_room.chat_id] = {}

        message_ids = []
        old_message_ids = []
        if message_type is not None:
            if (
                message_type not in self.message_tracking[chat_room.chat_id]
                or self.message_tracking[chat_room.chat_id][message_type] is None
            ):
                self.message_tracking[chat_room.chat_id][message_type] = []

            else:
                old_message_ids = self.message_tracking[chat_room.chat_id][message_type]
                for message_id in self.message_tracking[chat_room.chat_id][
                    message_type
                ]:
                    self.safe_delete_message(
                        context=context, chat_room=chat_room, message_id=message_id
                    )

            # Process list of messages
            if isinstance(message, list):
                if len("".join(message)) > MAX_MESSAGE_LENGTH:
                    # Break up the send into multiple messages
                    for message in message:
                        message_ids.append(
                            self.send_message(
                                context=context,
                                chat_room=chat_room,
                                message=message,
                                **kwargs,
                            )
                        )
                else:
                    # Send the message as a single message
                    message_ids.append(
                        self.send_message(
                            context=context,
                            chat_room=chat_room,
                            message=message,
                            **kwargs,
                        )
                    )

            # Process a single message
            elif isinstance(message, str):
                for chunk in [
                    str[i : i + MAX_MESSAGE_LENGTH]
                    for i in range(0, len(str), MAX_MESSAGE_LENGTH)
                ]:
                    message_ids.append(
                        self.send_message(
                            context=context,
                            chat_room=chat_room,
                            message=chunk,
                            **kwargs,
                        )
                    )

            else:
                self.logger.warning(f"Unknown message type {type(message)}")

        # Update the message tracking
        new_message_id_string = ",".join([str(id) for id in message_ids])
        old_message_id_string = ",".join([str(id) for id in old_message_ids])
        self.logger.debug(
            f"New message IDs: {new_message_id_string}, Old message IDs: {old_message_id_string}"
        )

        if message_type is not None:
            self.message_tracking[chat_room.chat_id][message_type] = message_ids

        return message_ids
