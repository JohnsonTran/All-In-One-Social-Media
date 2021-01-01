import tweepy
import requests

from os import environ
from dotenv import load_dotenv, find_dotenv
from post import Post

load_dotenv(find_dotenv())

auth = tweepy.OAuthHandler(environ.get('TWITTER_CONSUMER_KEY'), environ.get('TWITTER_CONSUMER_SECRET')) 
auth.set_access_token(environ.get('TWITTER_ACCESS_TOKEN'), environ.get('TWITTER_ACCESS_SECRET'))
api = tweepy.API(auth)

def get_twitter_embed_and_time(twitter_name):
    embed_url = 'https://publish.twitter.com/oembed'
    posts = []
    if twitter_name:
        # get the 20 latest tweets for an account
        for tweet in tweepy.Cursor(api.user_timeline, screen_name=twitter_name, include_rts=False).items(20):
            # get date of tweet:
            time_posted = tweet.created_at
            # get the tweet
            tweet_url = f'https://www.twitter.com/{twitter_name}/status/' + tweet.id_str
            # get the embed for the tweet
            params = {'url': tweet_url, 'omit_script': 't'}
            embed = requests.get(embed_url, params=params).json()['html']
            posts.append((time_posted, embed))
    
    return posts
