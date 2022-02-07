import typing
from datetime import datetime, timedelta
import html
import json
import logging
import os
from pprint import pprint
import random
import traceback
from typing import ContextManager, Union

from telegram import ParseMode, Update, ChatMember, Message, Chat, User
import telegram
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackContext,
    MessageHandler,
    Filters,
)

from tg_shill_bot.model import *

from tg_shill_bot.data_sources.reddit import RedditDataSource
from tg_shill_bot.data_sources.twitter import TwitterDataSource

BOT_NAME = "CryptoShillBot"
DEVELOPER_CHAT_ID = 2073823656
MAX_MESSAGE_LENGTH = 4096


class TelegramBot(object):
    def __init__(self, token: str, db_session) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.token = token
        self.db_session = db_session

        self.message_tracking = {}
        chats = self.db_session.query(ShillChatRoomSettings).all()
        for chat in chats:
            self.message_tracking[chat.chat_id] = {
                "last_scrape_message": None,
                "last_update_message": None,
            }

        self.updater = Updater(token=self.token)
        self.job_queue = self.updater.job_queue
        self.dispatcher = self.updater.dispatcher

        self.dispatcher.add_handler(
            MessageHandler(
                Filters.status_update.new_chat_members, self.new_chat_members
            )
        )
        self.dispatcher.add_handler(CommandHandler("start", self.start))
        self.dispatcher.add_handler(CommandHandler("help", self.help))
        self.dispatcher.add_handler(CommandHandler("list_types", self.list_types))
        self.dispatcher.add_handler(CommandHandler("list_sources", self.list_sources))
        self.dispatcher.add_handler(CommandHandler("links", self.list_links))
        self.dispatcher.add_handler(CommandHandler("frequency", self.frequency))
        self.dispatcher.add_handler(
            MessageHandler(Filters.text & ~Filters.command, self.message)
        )
        self.dispatcher.add_handler(CommandHandler("scrape", self.manual_scrape))

        self.dispatcher.add_error_handler(self.error_handler)

        self.job_queue.run_repeating(
            self.show_recent_links, interval=60 * 15, first=6 * 5
        )
        # self.job_queue.run_repeating(self.check_monitored, interval=60, first=0)
        self.job_queue.run_repeating(self.scrape_data, interval=60 * 60, first=0)

        self.updater.start_polling()
        self.updater.idle()

    def error_handler(self, update: object, context: CallbackContext) -> None:
        """Log the error and send a telegram message to notify the developer."""
        # Log the error before we do anything else, so we can see it even if something breaks.
        self.logger.error(
            msg="Exception while handling an update:", exc_info=context.error
        )

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

        # Finally, send the message
        self.__refresh_tracked_message(
            context=context,
            chat_id=DEVELOPER_CHAT_ID,
            message=message,
            parse_mode=ParseMode.HTML,
        )

    def new_chat_members(self, update: Update, context: CallbackContext) -> None:
        """Add a new user to the chat"""
        if update.message is None:
            return

        chat_id = update.message.chat_id

        for member in update.message.new_chat_members:
            if member.username == BOT_NAME:
                chat_settings = (
                    self.db_session.query(ShillChatRoomSettings)
                    .filter(ShillChatRoomSettings.chat_id == chat_id)
                    .first()
                )
                if chat_settings is None:
                    self.db_session.add(
                        ShillChatRoomSettings(
                            chat_id=chat_id,
                            name=update.message.chat.title,
                            toekn="",
                            cta_link="",
                            cta_text="SHILL and Grow!",
                            tags="",
                            scrape_interval=60 * 60,
                            update_interval=60 * 15,
                        )
                    )

                context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Thanks for adding me to {update.message.chat.title}, time to shill this thing!!!",
                )
            else:
                context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Welcome {member.name}, may the shilling commence!",
                )

    def start(self, update: Update, context: CallbackContext) -> None:
        """Send message on how to use the bot"""
        update.message.reply_text(
            "Beep boop. Crypto Shill Bot ready for action. /help for commands."
        )

    def help(self, update: Update, context: CallbackContext) -> None:
        """Send message with the list of available commands."""
        update.message.reply_text(
            """
/help - Show this message

Data Source Commands
/list_types - List all data source types
/list_sources <type> - List all data sources of the given type [twitter, reddit]
/links <- List recently known links

Scraping Configuration Commands
/scrape - Scrape data from all sources
/add_keyword - Add a keyword to monitor
/remove_keyword - Remove a keyword from monitor
/list_keywords - List all keywords being monitored
/frequency - Edit the frequency of social media scraping

Monitoring Commands
/add_monitor_keyword - Add a monitoring 
/remove_monitor_keyword - Remove a monitoring keyword
/list_monitor_keywords - List all keywords being monitored
/flush_monitors - Flush all monitors
"""
        )

    def list_types(self, update: Update, context: CallbackContext) -> None:
        """List all data source types"""
        chat_id = update.message.chat_id

        try:
            update.message.reply_text(
                """
Data Source Types:
- twitter
- reddit
            """
            )

        except (IndexError, ValueError):
            update.message.reply_text("Usage: /list_types")

        self.__safe_delete_message(context, chat_id, update.message.message_id)

    def list_sources(self, update: Update, context: CallbackContext) -> None:
        """List all data sources of the given type"""
        if update.message is None:
            return

        chat_id = update.message.chat_id

        try:
            data_source_type = context.args[0]

            reply_text = ""

            if data_source_type == "twitter":
                reply_text = "🐦🐦 Datasources 🐦🐦\n"
            elif data_source_type == "reddit":
                reply_text = "🤖🤖 Datasources 🤖🤖\n"

            data_sources = (
                self.db_session.query(ShillDataSource)
                .filter(
                    ShillDataSource.chat_id == chat_id,
                    ShillDataSource.data_source_type == data_source_type,
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

    def list_links(self, update: Update, context: CallbackContext) -> None:
        """List recently known links"""
        if update.message is None:
            return

        chat_id = update.message.chat_id

        self.__post_recent_links(context, chat_id)

        self.__safe_delete_message(context, chat_id, update.message.message_id)

    def __post_recent_links(self, context, chat_id=None):
        try:
            start_time = datetime.utcnow() - timedelta(hours=1)

            reddit_links = (
                self.db_session.query(ShillLinkTracker)
                .filter(
                    ShillLinkTracker.chat_id == chat_id,
                    ShillLinkTracker.created_at > start_time,
                    ShillLinkTracker.link_type == "reddit",
                )
                .order_by(ShillLinkTracker.created_at.desc())
                .all()
            )

            twitter_links = (
                self.db_session.query(ShillLinkTracker)
                .filter(
                    ShillLinkTracker.chat_id == chat_id,
                    ShillLinkTracker.created_at > start_time,
                    ShillLinkTracker.link_type == "twitter",
                )
                .order_by(ShillLinkTracker.created_at.desc())
                .all()
            )

            chat_settings = (
                self.db_session.query(ShillChatRoomSettings)
                .filter(ShillChatRoomSettings.chat_id == chat_id)
                .first()
            )

            self.generate_shill_call_text(
                context, chat_id, reddit_links, twitter_links, chat_settings
            )

        except (IndexError, ValueError):
            context.bot.send_message(chat_id=chat_id, text="Usage: /links")

    def frequency(self, update: Update, context: CallbackContext) -> None:
        """Edit the frequency of social media scraping"""
        if update.message is None:
            return

        chat_id = update.message.chat_id

        self.__safe_delete_message(context, chat_id, update.message.message_id)

    def message(self, update: Update, context: CallbackContext) -> None:
        """Handle chat text"""
        if update.message is None:
            return

        chat_id = update.message.chat_id

        reddit_links = RedditDataSource.link_pattern.findall(update.message.text)
        twitter_links = TwitterDataSource.link_pattern.findall(update.message.text)

        for link in reddit_links:
            reddit_link = RedditDataSource.link_pattern.search(link[0])

            if reddit_link is not None:
                self.logger.debug("Reddit link found")

            ds_name = reddit_link.group("name")
            ds_id = reddit_link.group("id")

            known_ds = (
                self.db_session.query(ShillDataSource)
                .filter(
                    ShillDataSource.chat_id == chat_id,
                    ShillDataSource.data_source_type == "reddit",
                    ShillDataSource.name == ds_name,
                )
                .first()
            )
            if not known_ds:
                new_ds = ShillDataSource(
                    chat_id=chat_id, data_source_type="reddit", name=ds_name.lower()
                )
                self.db_session.add(new_ds)
                self.db_session.commit()

                # update.message.reply_text(f"Added new Reddit data source: r/{ds_name}")

            # Add monitoring for this link
            if ds_id is not None:
                known_tracking = (
                    self.db_session.query(ShillLinkTracker)
                    .filter(
                        ShillLinkTracker.chat_id == chat_id,
                        ShillLinkTracker.link == link[0],
                    )
                    .first()
                )
                if not known_tracking:
                    new_tracking = ShillLinkTracker(
                        chat_id=chat_id, link=link[0], link_type="reddit"
                    )
                    self.db_session.add(new_tracking)
                    self.db_session.commit()

                    # update.message.reply_text(f"Tracking new Reddit link")

        for link in twitter_links:
            twitter_link = TwitterDataSource.link_pattern.search(link[0])

            if twitter_link is not None:
                self.logger.debug("Twitter link found")

            ds_name = twitter_link.group("name")
            ds_id = twitter_link.group("id")

            known_ds = (
                self.db_session.query(ShillDataSource)
                .filter(
                    ShillDataSource.chat_id == chat_id,
                    ShillDataSource.data_source_type == "twitter",
                    ShillDataSource.name == ds_name,
                )
                .first()
            )
            if not known_ds:
                new_ds = ShillDataSource(
                    chat_id=chat_id, data_source_type="twitter", name=ds_name.lower()
                )
                self.db_session.add(new_ds)
                self.db_session.commit()

                # update.message.reply_text(f"Added new Twitter data source: @{ds_name}")

            # Add monitoring for this link
            if ds_id is not None:
                known_tracking = (
                    self.db_session.query(ShillLinkTracker)
                    .filter(
                        ShillLinkTracker.chat_id == chat_id,
                        ShillLinkTracker.link == link[0],
                    )
                    .first()
                )
                if not known_tracking:
                    new_tracking = ShillLinkTracker(
                        chat_id=chat_id, link=link[0], link_type="twitter"
                    )
                    self.db_session.add(new_tracking)
                    self.db_session.commit()

                    # update.message.reply_text(f"Tracking new Twitter link")

    def show_recent_links(self, context: CallbackContext) -> None:
        """Show recent links"""
        self.logger.debug("Sending recent links listing")

        chats = self.db_session.query(ShillChatRoomSettings).all()
        for chat in chats:
            self.logger.debug(
                "Sending recent links listing for chat_id: %s", chat.chat_id
            )
            self.__post_recent_links(context, chat.chat_id)

    def manual_scrape(self, update: Update, context: CallbackContext) -> None:
        """Maually trigger social scrape"""
        if update.message is None:
            return

        chat_id = update.message.chat_id

        self.social_scrape(context, chat_id=chat_id)

        self.__safe_delete_message(context, chat_id, update.message.message_id)

    def scrape_data(self, context: CallbackContext) -> None:
        """Scrape data from social media"""
        self.logger.debug("Scraping data")

        chats = self.db_session.query(ShillChatRoomSettings).all()

        # TODO: Reschedule this job

        for chat in chats:
            self.social_scrape(context, chat_id=chat.chat_id)

    def social_scrape(self, context: CallbackContext, chat_id: int) -> None:
        bot_message = context.bot.send_message(
            chat_id=chat_id,
            text="🤖 Beep boop - Please be patient while I check the socials...",
        )

        message_text = "👇👇 📣📣 SHillcall - New Socials 📣📣 👇👇\n\n"

        sample_posts = self.__scrape_reddit_feeds(chat_id)

        if len(sample_posts) > 0:
            message_text += "🤖🤖 Check Out These Recent Posts 🤖🤖\n\n"

            for post in sample_posts:
                message_text += f"{post}\n"

                known_tracking = (
                    self.db_session.query(ShillLinkTracker)
                    .filter(
                        ShillLinkTracker.chat_id == chat_id,
                        ShillLinkTracker.link == post,
                    )
                    .first()
                )
                if not known_tracking:
                    new_tracking = ShillLinkTracker(
                        chat_id=chat_id, link=post, link_type="reddit"
                    )
                    self.db_session.add(new_tracking)
                    self.db_session.commit()

            message_text += "\n🤖🤖 Unchecked For Quality - Discretion Requested 🤖🤖\n\n"

        sample_tweets = self.__scrape_twitter_feeds(chat_id)

        if len(sample_tweets) > 0:
            message_text += "🐦🐦 Check Out These Recent Tweets 🐦🐦\n\n"

            for tweet in sample_tweets:
                message_text += f"{tweet}\n"

                known_tracking = (
                    self.db_session.query(ShillLinkTracker)
                    .filter(
                        ShillLinkTracker.chat_id == chat_id,
                        ShillLinkTracker.link == tweet,
                    )
                    .first()
                )
                if not known_tracking:
                    new_tracking = ShillLinkTracker(
                        chat_id=chat_id, link=tweet, link_type="twitter"
                    )
                    self.db_session.add(new_tracking)
                    self.db_session.commit()

            message_text += "\n🐦🐦 Unchecked For Quality - Discretion Requested 🐦🐦"

        # Remove Beep boop message
        if bot_message is not None:
            self.__safe_delete_message(context, chat_id, bot_message.message_id)

        self.__refresh_tracked_message(
            context=context,
            chat_id=chat_id,
            message=[message_text],
            message_type="last_scrape_message",
        )

    def check_monitored(self, context: CallbackContext) -> None:
        """Check if any monitored data sources have new data"""
        self.logger.debug("Checking monitored data sources")

    def generate_shill_call_text(
        self, context, chat_id, reddit_links, twitter_links, chat_settings
    ):
        reddit_text = "🤖🤖 Check These Reddit Posts 🤖🤖\n\n"
        if len(reddit_links) > 0:
            for reddit_link in reddit_links:
                reddit_text += f"{reddit_link.link}\n"

            reddit_text += "\n🤖🤖 ⬆️ & 📣 🤖🤖\n\n"
        else:
            reddit_text += "🤖🤖 So much empty?! - Feed ME! 🤖🤖\n\n"

        twitter_text = "🐦🐦 Check These Tweets 🐦🐦\n\n"
        if len(twitter_links) > 0:
            for twitter_link in twitter_links:
                twitter_text += f"{twitter_link.link}\n"

            twitter_text += "\n🐦🐦 💓 & Retweet & Follow 🐦🐦\n\n"
        else:
            twitter_text += "🐦🐦 So much empty?! - Feed ME! 🐦🐦\n\n"

        general_text = "🤩🤩 General Hygiene 🤩🤩\n\n"
        if chat_settings is not None:
            if chat_settings.dex_link is not None:
                general_text += f"💹💹 Dextools 💹💹\n\n"
                general_text += f"{chat_settings.dex_link} \n\n"
                general_text += f"💹💹 ⭐ | Click Links 💹💹\n\n"

            if chat_settings.cmc_link is not None or chat_settings.cg_link is not None:
                general_text += f"📣📣 Listing Sites 📣📣\n\n"

                if chat_settings.cmc_link is not None:
                    general_text += f"🌐 {chat_settings.cmc_link}\n"

                if chat_settings.cg_link is not None:
                    general_text += f"🦎 {chat_settings.cg_link}\n"

                general_text += "\n📣📣 ⭐ | ⬆️ | Comment 📣📣\n\n"

            if chat_settings.cta_link is not None:
                general_text += f"🔗 {chat_settings.cta_link}\n\n"

            if chat_settings.tags is not None:
                general_text += f"🚩 {chat_settings.tags}\n\n"

            if chat_settings.cta_text is not None:
                general_text += f"{chat_settings.cta_text}\n\n"

        else:
            general_text = "\n\n"

        reply_text = "👇👇 📣📣 SHillcall! 📣📣 👇👇\n\n"

        end_text = ""
        if chat_settings.token is not None:
            end_text += f"👆👆 Help {chat_settings.token} grow! 👆👆"
        else:
            end_text += "👆👆 Help us grow! 👆👆"

        self.__refresh_tracked_message(
            context=context,
            chat_id=chat_id,
            message=[reply_text, reddit_text, twitter_text, general_text, end_text],
            message_type="shill_call_message",
        )

    def __scrape_reddit_feeds(self, chat_id: int) -> typing.List[str]:
        """Scrape reddit feeds"""
        reddit_ds = RedditDataSource(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        )

        reddit_sources = (
            self.db_session.query(ShillDataSource)
            .filter(ShillDataSource.data_source_type == "reddit")
            .all()
        )

        recent_posts = []
        for subreddit in reddit_sources:
            print(f"Getting posts from {subreddit.name}")
            recent_posts += reddit_ds.get_recent(subreddit=subreddit.name)

        sample_posts = (
            random.sample(recent_posts, 20) if len(recent_posts) > 20 else recent_posts
        )
        return sample_posts

    def __scrape_twitter_feeds(self, chat_id: int) -> typing.List[str]:
        """Scrape twitter feeds"""
        twitter_ds = TwitterDataSource(
            api_key=os.environ["TWITTER_API_KEY"],
            api_key_secret=os.environ["TWITTER_API_KEY_SECRET"],
            bearer_token=os.environ["TWITTER_BEARER_TOKEN"],
        )

        twitter_sources = (
            self.db_session.query(ShillDataSource)
            .filter(
                ShillDataSource.chat_id == chat_id,
                ShillDataSource.data_source_type == "twitter",
                ShillDataSource.ignore == False,
            )
            .all()
        )

        recent_tweets = []
        for user in twitter_sources:
            for tweet in twitter_ds.get_recent(tweet_user=user.name):
                known_tracking = (
                    self.db_session.query(ShillLinkTracker)
                    .filter(
                        ShillLinkTracker.chat_id == chat_id,
                        ShillLinkTracker.link == tweet,
                    )
                    .first()
                )
                if not known_tracking:
                    recent_tweets.append(tweet)

        sample_tweets = (
            random.sample(recent_tweets, 20)
            if len(recent_tweets) > 20
            else recent_tweets
        )
        return sample_tweets

    def __safe_delete_message(
        self, context: ContextManager, chat_id: int, message_id: int
    ) -> None:
        """Safely delete a message and squash error"""
        try:
            context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except telegram.error.BadRequest:
            self.logger.warning(
                f"Failed to delete message {message_id} in chat {chat_id}"
            )

    def __refresh_tracked_message(
        self,
        context: ContextManager,
        chat_id: int,
        message: Union[str, list[str]],
        message_type: str = None,
        **kwargs,
    ) -> list[int]:
        """Refresh tracked message"""
        if chat_id not in self.message_tracking:
            self.message_tracking[chat_id] = {}

        old_message_ids = []
        if message_type is not None:
            if message_type not in self.message_tracking[chat_id] or self.message_tracking[chat_id][message_type] is None:
                self.message_tracking[chat_id][message_type] = []

            else:
                old_message_ids = self.message_tracking[chat_id][message_type]
                for message_id in self.message_tracking[chat_id][message_type]:
                    self.__safe_delete_message(context, chat_id, message_id)

            self.message_tracking[chat_id][message_type] = []

            if isinstance(message, list):
                if len("".join(message)) > MAX_MESSAGE_LENGTH:
                    # Break up the send into multiple messages
                    for message in message:
                        message_id = context.bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            disable_web_page_preview=True,
                            **kwargs,
                        ).message_id

                        if message_type is not None:
                            self.message_tracking[chat_id][message_type].append(
                                message_id
                            )
                else:
                    # Send the message as a single message
                    self.message_tracking[chat_id][message_type].append(
                        context.bot.send_message(
                            chat_id=chat_id,
                            text="".join(message),
                            disable_web_page_preview=True,
                            **kwargs,
                        ).message_id
                    )
            elif isinstance(message, str):
                for chunk in [
                    str[i : i + MAX_MESSAGE_LENGTH]
                    for i in range(0, len(str), MAX_MESSAGE_LENGTH)
                ]:
                    self.message_tracking[chat_id][message_type].append(
                        context.bot.send_message(
                            chat_id=chat_id,
                            text=chunk,
                            disable_web_page_preview=True,
                            **kwargs,
                        ).message_id
                    )

        new_message_id_string = ",".join(
            [str(id) for id in self.message_tracking[chat_id][message_type]]
        )
        old_message_id_string = ",".join([str(id) for id in old_message_ids])
        self.logger.debug(
            f"New message IDs: {new_message_id_string}, Old message IDs: {old_message_id_string}"
        )

        return self.message_tracking[chat_id][message_type]
