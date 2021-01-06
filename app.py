from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy 
from flask_login import LoginManager
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_caching import Cache
from os import environ
from flask_celery import make_celery
from celery import Celery

from twitter import get_twitter_embed_and_time
from instagram import get_instagram_embed_and_time
from youtube import get_youtube_embed_and_time

celery = Celery(__name__, broker=environ.get('REDIS_SERVER_URL'),                       
                backend=environ.get('REDIS_SERVER_URL'))
cache = Cache(config={'CACHE_TYPE': 'simple'})
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('SQLALCHEMY_DATABASE_URI')
    app.config.update(
        CELERY_BROKER_URL=environ.get('REDIS_SERVER_URL'),
        CELERY_RESULT_BACKEND=environ.get('REDIS_SERVER_URL')
    )

    celery = make_celery(app)

    cache.init_app(app)

    db.init_app(app)

    from models.people_model import Person
    db.create_all(app=app)

    from views.home import home_bp
    app.register_blueprint(home_bp)

    from views.admin import admin
    admin.init_app(app)

    return app

@celery.task()
def get_youtube(youtube_id, next_page_token):
    youtube_posts = []
    if youtube_id:
        youtube_posts = get_youtube_embed_and_time(youtube_id, next_page_token)
    return youtube_posts

@celery.task()
def get_twitter(twitter_name, page_num):
    twitter_posts = []
    if twitter_name:
        twitter_posts = get_twitter_embed_and_time(twitter_name, page_num)
    return twitter_posts

@celery.task()
def get_instagram(instagram_name):
    instagram_posts = []
    if instagram_name:
        instagram_posts = get_instagram_embed_and_time(instagram_name)
    return instagram_posts
