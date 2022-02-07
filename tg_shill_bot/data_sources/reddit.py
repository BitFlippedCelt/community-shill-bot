import logging
from pprint import pprint
import re
import os
import typing

import praw
from nltk.sentiment import SentimentIntensityAnalyzer

from tg_shill_bot.data_sources import SocialDataSource


class RedditDataSource(SocialDataSource):
    sia = SentimentIntensityAnalyzer()

    link_pattern = re.compile(
        r"(https?://(?:www\.)?reddit\.com/r/(?P<name>\w+)(/comments/(?P<id>\w+(?:/\w+)?))?)"
    )

    def __init__(self, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initializing RedditDataSource")

        self.name = "reddit"
        self.api = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent="tg_shill by u/bitflipped",
        )

    def get_recent(self, **kwargs):
        upvotes = 5
        if "upvotes" in kwargs:
            upvotes = kwargs["upvotes"]

        if "subreddit" in kwargs:
            subreddit = self.api.subreddit(kwargs["subreddit"])
            new_posts = subreddit.new(limit=20)

            filtered_new_posts = []
            for post in new_posts:
                if not post.stickied and post.is_self:
                    score = self.sia.polarity_scores(post.title)["compound"]
                    if score > 0:
                        filtered_new_posts.append(post.url)

            return filtered_new_posts

        return []

    def check_engagement(self, **kwargs):
        pass
