import logging
from pprint import pprint
import re
import os

from youtubesearchpython import *
import praw
from nltk.sentiment import SentimentIntensityAnalyzer

from tg_shill_bot.data_sources import SocialDataSource


class YoutubeDataSource(SocialDataSource):
    link_pattern = re.compile(
        r"(https?://(?:www\.)?youtube\.com/(c/(?P<name>\w+(?:/\w+)?)?|watch\?v=(?P<id>\w+(?:/\w+)?)))"
    )

    def __init__(self, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initializing YoutubeDataSource")

        self.name = "youtube"

    def get_recent(self, **kwargs):
        video_search = CustomSearch(
            query="crypto", searchPreferences="CAMSBAgBEAE%253D", limit=10
        )

        filtered_new_posts = []
        for video in video_search.result()["result"]:
            filtered_new_posts.append(video["link"])

        return filtered_new_posts

    def check_engagement(self, **kwargs):
        pass
