import os
from pprint import pprint
import re
import logging
from datetime import datetime, timedelta

import tweepy
from nltk.sentiment import SentimentIntensityAnalyzer

from tg_shill_bot.data_sources import SocialDataSource


class TwitterDataSource(SocialDataSource):
    sia = SentimentIntensityAnalyzer()

    link_pattern = re.compile(
        r"(https?://(?:www\.)?twitter\.com/(?P<name>\w+)(/status/(?P<id>\d+))?)"
    )

    def __init__(self, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initializing TwitterDataSource")

        self.name = "twitter"
        self.api = tweepy.Client(
            access_token=kwargs["api_key"],
            access_token_secret=kwargs["api_key_secret"],
            bearer_token=kwargs["bearer_token"],
            return_type=dict,
        )

    def get_recent(self, **kwargs):
        if "tweet_user" not in kwargs:
            return []

        tweet_user = kwargs["tweet_user"]

        twitter_user = self.api.get_user(username=tweet_user)

        if "data" not in twitter_user:
            self.logger.warning(f"{tweet_user} is not a valid Twitter user")
            return []
        else:
            twitter_user = twitter_user["data"]

        start_time = datetime.utcnow() - timedelta(hours=1)
        start_time_string = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        tweets = self.api.get_users_tweets(
            twitter_user["id"], start_time=start_time_string, max_results=5
        )

        recent_tweets = []
        if "data" in tweets:
            for tweet in tweets["data"]:
                score = self.sia.polarity_scores(tweet["text"])["compound"]
                if score > 0:
                    recent_tweets.append(
                        f"https://twitter.com/{tweet_user}/status/{tweet['id']}"
                    )

        return recent_tweets

    def check_engagement(self, **kwargs):
        tweet_url = kwargs["tweet_url"]
        tags = kwargs["tags"]

        tweet = TwitterDataSource.link_pattern.match(tweet_url)
        if tweet is not None:
            tweet_user = tweet.group("name")
            tweet_id = tweet.group("id")

            retweets = self.api.get_retweeters(tweet_id)
            for retweet in retweets["data"]:

                self.logger.info(
                    f"{retweet['username']} retweeted {tweet_user}'s tweet {tweet_id}"
                )
