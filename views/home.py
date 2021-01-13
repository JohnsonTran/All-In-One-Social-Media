from flask import Blueprint, render_template, request, jsonify, json
from wtforms import StringField, TextField, Form
from wtforms.validators import DataRequired
from models.people_model import Person
from app import db, cache, celery, get_instagram, get_twitter, get_youtube, cache_instagram_posts
from post import Post
from celery import group

home_bp = Blueprint("home_bp", __name__)

class SearchForm(Form):
    person = StringField('Person', validators=[DataRequired()], render_kw={"placeholder": "person"})

@home_bp.route("/")
def home_page():
    form = SearchForm(request.args)
    return render_template("home.html", form=form)

@home_bp.route("/people")
def peopledic():
    res = Person.query.all()
    list_people = [r.as_dict() for r in res]
    return jsonify(list_people)

@home_bp.route("/process", methods=['GET'])
def process():
    person = request.args.get('person')
    form = SearchForm(request.args)
    if person:
        person_info = Person.query.filter_by(name=person).first()
        twitter_name = person_info.twitter
        youtube_id = person_info.youtube_id
        instagram_name = person_info.instagram

        cache.set('twitter_name', twitter_name)
        cache.set('youtube_id', youtube_id)
        cache.set('instagram_name', instagram_name)
        cache.set('instagram_cache', [])

        posts = []

        job = group([get_instagram.s(instagram_name), 
                    get_twitter.s(twitter_name, 1), 
                    get_youtube.s(youtube_id, None)])
        result = job.apply_async()
        real_res = result.join()
        instagram_res = real_res[0]
        twitter_res = real_res[1]
        youtube_res, youtube_next_page_token = real_res[2]

        cache.set('youtube_next_page_token', youtube_next_page_token)

        youtube_embeds = []
        for post in youtube_res:
            time_posted, embed = post
            youtube_embeds.append(embed)
            posts.append(Post('youtube', time_posted, embed))

        twitter_embeds = []
        for post in twitter_res:
            time_posted, embed = post
            twitter_embeds.append(embed)
            posts.append(Post('twitter', time_posted, embed))

        instagram_embeds = []
        for post in instagram_res:
            time_posted, embed = post
            instagram_embeds.append(embed)
            posts.append(Post('instagram', time_posted, embed))

        posts.sort(key=lambda x: x.time_posted, reverse=True)

        embeds = []
        for post in posts:
            embeds.append(post.embed)

        tabs = ['<li class="nav-tab active" id="all" onclick="showAll();">All</li>']   
        if twitter_res:
            tabs.append('<li class="nav-tab" id="twitter" onclick="showTwitter();">Twitter</li>')
        if instagram_res:
            tabs.append('<li class="nav-tab" id="instagram" onclick="showInstagram();">Instagram</li>')
        if youtube_res:
            tabs.append('<li class="nav-tab" id="youtube" onclick="showYoutube();">YouTube</li>')

        data = {'embeds': embeds, 'tabs': tabs, 'twitter': twitter_embeds, 'instagram': instagram_embeds, 'youtube': youtube_embeds}

        return render_template('profile.html', form=form, data=data)
        # return jsonify({'embeds': embeds, 'tabs': tabs, 'twitter': twitter_embeds, 'instagram': instagram_embeds, 'youtube': youtube_embeds})
    
    return render_template('profile.html', form=form, data={})
    # return jsonify({'error': 'missing data...'})

# gets more twitter data and returns it as a json
@home_bp.route("/load-twitter")
def load_twitter():
    if request.args:
        twitter_name = cache.get('twitter_name')
        counter = int(request.args.get('c'))
        print(counter)

        result = get_twitter.delay(twitter_name, counter)
        twitter_res = result.get()
        
        twitter_embeds = []
        for post in twitter_res:
            time_posted, embed = post
            twitter_embeds.append(embed)
        
        return jsonify({'twitter': twitter_embeds})
    
    return jsonify({})

# gets more youtube data and returns it as a json
@home_bp.route("/load-youtube")
def load_youtube():
    youtube_id = cache.get('youtube_id')
    next_page_token = cache.get('youtube_next_page_token')

    result = get_youtube.delay(youtube_id, next_page_token)
    youtube_res, youtube_next_page_token = result.get()

    cache.set('youtube_next_page_token', youtube_next_page_token)
    
    youtube_embeds = []
    for post in youtube_res:
        time_posted, embed = post
        youtube_embeds.append(embed)
    
    return jsonify({'youtube': youtube_embeds})

# gets more instagram posts and caches it for later
@home_bp.route("/cache-instagram")
def cache_instagram():
    instagram_name = cache.get('instagram_name')

    result = cache_instagram_posts.delay(instagram_name)
    instagram_res = result.get()

    cache.set('instagram_cache', instagram_res)
    print(instagram_res)
    return jsonify({'success': True})

# gets more instagram posts and caches it for later
from os import environ
from dotenv import load_dotenv, find_dotenv
import requests
load_dotenv(find_dotenv())
@home_bp.route("/load-instagram")
def load_instagram():
    if request.args:
        instagram_name = cache.get('instagram_name')
        counter = int(request.args.get('c'))

        instagram_embeds = []
        instagram_url = 'https://www.instagram.com'
        embed_url = 'https://graph.facebook.com/v9.0/instagram_oembed'
        access_token = environ.get('INSTAGRAM_APP_ID') + '|' + environ.get('INSTAGRAM_CLIENT_ID')

        # busy wait until the posts are put into the cache
        while cache.get('instagram_cache') == []:
            pass

        instagram_cache = cache.get('instagram_cache')

        # delay embed request to lower the chance of reaching the embed API limit
        for post in instagram_cache[counter * 12: (counter + 1) * 12]:
            post_name = post
            post_url = instagram_url + post_name
            
            params = {'url': post_url, 'access_token': access_token, 'omitscript': 'true'}
            embed = requests.get(embed_url, params).json()['html']
            instagram_embeds.append(embed)
        
        return jsonify({'instagram': instagram_embeds})
    
    return jsonify({})
