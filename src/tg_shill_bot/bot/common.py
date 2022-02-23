from datetime import datetime, timedelta
import os
import typing
import random
import logging

from sqlalchemy.orm import sessionmaker

from tg_shill_bot.data_sources.reddit import RedditDataSource
from tg_shill_bot.data_sources.twitter import TwitterDataSource
from tg_shill_bot.data_sources.youtube import YoutubeDataSource
from tg_shill_bot.model import *
from tg_shill_bot.model import data_source


class CommonBot(object):
    BOT_NAME = "CryptoShillBot"

    def __init__(self, db_session: sessionmaker, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        self.db_session = db_session

        self.message_tracking = {}

    def error_handler(self, error: Exception) -> None:
        """Error handler"""
        # Log the error before we do anything else, so we can see it even if something breaks.
        self.logger.error(msg="Exception while handling an update:", exc_info=error)

    def get_chat_room(self, chat_id: int) -> typing.Optional[ChatRoom]:
        """Get chat room"""
        return self.db_session.query(ChatRoom).filter_by(chat_id=chat_id).first()

    def list_data_source_types(self) -> typing.List[str]:
        """List data source types"""
        return ["reddit", "twitter", "youtube"]

    def list_data_sources(self, chat_room: ChatRoom, data_source_type: str) -> str:
        """List data sources"""
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

    def store_link(
        self, chat_room: ChatRoom, link: typing.Match[str], ds_type: str
    ) -> None:
        """Store a link/datasource in the database"""
        ds_name = link.group("name")
        ds_id = link.group("id")

        known_ds = (
            self.db_session.query(DataSource)
            .filter(
                DataSource.chat_room_id == chat_room.id,
                DataSource.data_source_type == ds_type,
                DataSource.name == ds_name,
            )
            .first()
        )
        if known_ds is None:
            new_ds = DataSource(
                chat_room_id=chat_room.id,
                data_source_type=ds_type,
                name=ds_name.lower(),
            )
            self.db_session.add(new_ds)
            self.db_session.commit()

            self.logger.info(
                f"[{chat_room.chat_id}] Added new {ds_type} data source: {ds_name}"
            )

        # Add monitoring for this link
        if ds_id is not None:
            known_tracking = (
                self.db_session.query(LinkTracker)
                .filter(
                    LinkTracker.chat_room_id == chat_room.id,
                    LinkTracker.link == link[0],
                )
                .first()
            )
            if not known_tracking:
                new_tracking = LinkTracker(
                    chat_room_id=chat_room.id, link=link[0], link_type=ds_type
                )
                self.db_session.add(new_tracking)
                self.db_session.commit()

                self.logger.info(
                    f"[{chat_room.chat_id}] Tracking new {ds_type} link {link[0]}"
                )

    def get_links(
        self,
        chat_room: ChatRoom,
        link_type: str,
    ) -> typing.List[LinkTracker]:
        """Get links for a chat room and link type"""
        self.logger.info(
            f"Getting recent {link_type} links for chat {chat_room.chat_id}"
        )

        start_time = datetime.utcnow() - timedelta(minutes=chat_room.link_age)
        links = (
            self.db_session.query(LinkTracker)
            .filter(
                LinkTracker.chat_room_id == chat_room.id,
                LinkTracker.created_at > start_time,
                LinkTracker.link_type == link_type,
            )
            .order_by(LinkTracker.created_at.desc())
            .all()
        )

        if len(links) > chat_room.link_count:
            links = random.sample(links, chat_room.link_count)

        return links

    def scrape_reddit_feeds(self, chat_room: ChatRoom) -> typing.List[str]:
        """Scrape reddit feeds"""
        reddit_ds = RedditDataSource(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        )

        reddit_sources = (
            self.db_session.query(DataSource)
            .filter(
                DataSource.chat_room_id == chat_room.id,
                DataSource.data_source_type == "reddit",
                DataSource.ignore == False,
            )
            .all()
        )

        recent_posts = []
        for subreddit in reddit_sources:
            print(f"Getting posts from {subreddit.name}")
            recent_posts += reddit_ds.get_recent(subreddit=subreddit.name)

        if len(recent_posts) > chat_room.link_count:
            recent_posts = (
                random.sample(recent_posts, chat_room.link_count)
                if len(recent_posts) > chat_room.link_count
                else recent_posts
            )

        return recent_posts

    def scrape_twitter_feeds(self, chat_room: ChatRoom) -> typing.List[str]:
        """Scrape twitter feeds"""
        twitter_ds = TwitterDataSource(
            api_key=os.environ["TWITTER_API_KEY"],
            api_key_secret=os.environ["TWITTER_API_KEY_SECRET"],
            bearer_token=os.environ["TWITTER_BEARER_TOKEN"],
        )

        twitter_sources = (
            self.db_session.query(DataSource)
            .filter(
                DataSource.chat_room_id == chat_room.id,
                DataSource.data_source_type == "twitter",
                DataSource.ignore == False,
            )
            .all()
        )

        recent_tweets = []
        for user in twitter_sources:
            for tweet in twitter_ds.get_recent(tweet_user=user.name):
                known_tracking = (
                    self.db_session.query(LinkTracker)
                    .filter(
                        LinkTracker.chat_room_id == chat_room.id,
                        LinkTracker.link == tweet,
                    )
                    .first()
                )
                if not known_tracking:
                    recent_tweets.append(tweet)

        if len(recent_tweets) > chat_room.link_count:
            recent_tweets = (
                random.sample(recent_tweets, chat_room.link_count)
                if len(recent_tweets) > chat_room.link_count
                else recent_tweets
            )

        return recent_tweets

    def scrape_youtube_feeds(self, chat_room: ChatRoom) -> typing.List[str]:
        """Scrape Youtube feeds"""
        ds = YoutubeDataSource()

        data_sources = (
            self.db_session.query(DataSource)
            .filter(
                DataSource.chat_room_id == chat_room.id,
                DataSource.data_source_type == ds.name,
                DataSource.ignore == False,
            )
            .all()
        )

        recent_videos = []
        for recent_video in ds.get_recent():
            known_tracking = (
                self.db_session.query(LinkTracker)
                .filter(
                    LinkTracker.chat_room_id == chat_room.id,
                    LinkTracker.link == recent_video,
                )
                .first()
            )
            if not known_tracking:
                recent_videos.append(recent_video)

        if len(recent_videos) > chat_room.link_count:
            recent_videos = (
                random.sample(recent_videos, chat_room.link_count)
                if len(recent_videos) > chat_room.link_count
                else recent_videos
            )

        return recent_videos

    def generate_shill_call(
        self, chat_room: ChatRoom, compact: bool = False
    ) -> typing.List[str]:
        """Generate a shill call"""
        start_text = "👇👇 📣📣 SHillcall! 📣📣 👇👇\n" if not compact else ""

        # Get Reddit Links
        reddit_links = self.get_links(chat_room=chat_room, link_type="reddit")
        reddit_text = ""
        if len(reddit_links) > 0:
            reddit_text = "🤖🤖 Check These Reddit Posts 🤖🤖\n"
            for reddit_link in reddit_links:
                reddit_text += f"{reddit_link.link}\n"

            reddit_text += "🤖🤖 ⬆️ & 📣 🤖🤖\n\n"
        else:
            reddit_text += "🤖🤖 So much empty?! - Feed ME! 🤖🤖\n\n"

        # Get Twitter Links
        twitter_links = self.get_links(chat_room=chat_room, link_type="twitter")
        twitter_text = ""
        if len(twitter_links) > 0:
            twitter_text = "🐦🐦 Check These Tweets 🐦🐦\n"
            for twitter_link in twitter_links:
                twitter_text += f"{twitter_link.link}\n"

            twitter_text += "🐦🐦 💓 & Retweet & Follow 🐦🐦\n\n"
        else:
            twitter_text += "🐦🐦 So much empty?! - Feed ME! 🐦🐦\n\n"

        # Get Youtube Links
        youtube_links = self.get_links(chat_room=chat_room, link_type="youtube")
        youtube_text = ""
        if len(youtube_links) > 0:
            youtube_text = "🎥🎥 Check These Videos 🎥🎥\n"
            for youtube_link in youtube_links:
                youtube_text += f"{youtube_link.link}\n"

            youtube_text += "🎥🎥 Comment 🎥🎥\n\n"
        else:
            youtube_text += "🎥🎥 So much empty?! - Feed ME! 🎥🎥\n\n"

        if not compact:
            general_text = self.generate_general_shill_text(chat_room)

            end_text = ""
            if chat_room.token is not None:
                end_text += f"👆👆 Help {chat_room.token} grow! 👆👆"
            else:
                end_text += "👆👆 Help us grow! 👆👆"
        else:
            general_text = ""
            end_text = ""

        ad_text = self.generate_ad_text()

        return [
            start_text,
            reddit_text,
            twitter_text,
            youtube_text,
            general_text,
            end_text,
            ad_text,
        ]

    def generate_general_shill_text(self, chat_room: ChatRoom) -> str:
        """Generate general shill text"""
        general_text = "🤩🤩 General Hygiene 🤩🤩\n"

        if chat_room is not None:
            if chat_room.dex_link is not None:
                general_text += f"💹💹 Dextools 💹💹\n"
                general_text += f"{chat_room.dex_link} \n"
                general_text += f"💹💹 ⭐ | Click Links 💹💹\n"

            if chat_room.cmc_link is not None or chat_room.cg_link is not None:
                general_text += f"📣📣 Listing Sites 📣📣\n"

                if chat_room.cmc_link is not None:
                    general_text += f"🌐 {chat_room.cmc_link}\n"

                if chat_room.cg_link is not None:
                    general_text += f"🦎 {chat_room.cg_link}\n"

                general_text += "\n📣📣 ⭐ | ⬆️ | Comment 📣📣\n"

            if chat_room.cta_link is not None:
                general_text += f"🔗 {chat_room.cta_link}\n"

            if chat_room.tags is not None:
                general_text += f"🚩 {chat_room.tags}\n"

            if chat_room.cta_text is not None:
                general_text += f"{chat_room.cta_text}\n"

        else:
            general_text = "\n"
        return general_text

    def generate_ad_text(self):
        # Generate advertisement
        ad_text = ""

        ad = (
            self.db_session.query(Advertisement)
            .filter(
                Advertisement.created_at < datetime.now(),
                Advertisement.start_at < datetime.now(),
                Advertisement.end_at > datetime.now(),
            )
            .first()
        )

        if ad is not None:
            ad_text = f"👾 | <a href='{ad.link}'>{ad.name} ({ad.token})</a>"

            if len(ad.buy_link) > 0:
                ad_text += f" <a href='{ad.buy_link}'>💰</a>"

            if len(ad.chart_link) > 0:
                ad_text += f" <a href='{ad.chart_link}'>📈</a>"

            ad_text += " | 👾"

        return ad_text
