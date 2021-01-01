import os
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import googleapiclient.errors
from os import environ
from dotenv import load_dotenv, find_dotenv
from post import Post

load_dotenv(find_dotenv())

api_key = environ.get('YOUTUBE_API_KEY')

# create embed for a youtube video
def make_embed(videoId):
    return f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{videoId}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'

youtube = build('youtube', 'v3', developerKey=api_key)

def get_youtube_embed_and_time(youtube_id):
    posts = []
    if youtube_id:
        # get channel details
        content = youtube.channels().list(id=youtube_id, part='contentDetails').execute()
        # get the uploads playlist
        uploads_id = content['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        # get the 20 latest uploads
        uploads = youtube.playlistItems().list(playlistId=uploads_id, part='snippet', maxResults=20).execute()
        # get the embed for each upload
        for upload in uploads['items']:
            embed = make_embed(upload['snippet']['resourceId']['videoId'])
            time_posted = upload['snippet']['publishedAt']
            posts.append((time_posted, embed))
    
    return posts