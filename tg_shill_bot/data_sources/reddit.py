import logging
import re
import os

import praw

from tg_shill_bot.data_sources import SocialDataSource


class RedditDataSource(SocialDataSource):
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

        subreddit = self.api.subreddit(kwargs["subreddit"])
        new_posts = subreddit.new(limit=10)

        trending_posts = []
        for post in new_posts:
            if post.score >= upvotes:
                trending_posts.append(post)

        return trending_posts

    def check_engagement(self, **kwargs):
        pass