from flask import Blueprint, render_template, request, jsonify, json, redirect, url_for
from wtforms import StringField, TextField, Form
from wtforms.validators import DataRequired
from models.people_model import Person
from app import db, cache, celery, get_instagram, get_twitter, get_youtube
from post import Post
from celery import group

home_bp = Blueprint("home_bp", __name__)

class SearchForm(Form):
    person = StringField('Person', validators=[DataRequired()], render_kw={"placeholder": "person"})

@home_bp.route("/")
def home_page():
    form = SearchForm(request.form)
    return render_template("home.html", form=form)

@home_bp.route("/people")
def peopledic():
    res = Person.query.all()
    list_people = [r.as_dict() for r in res]
    return jsonify(list_people)

@home_bp.route("/process", methods=['POST'])
def process():
    person = request.form['person']
    return redirect(url_for('home_bp.result', person=person))

@home_bp.route("/<person>")
@cache.cached(timeout=1800)
def result(person):
    form = SearchForm(request.form)
    if person:
        person_info = Person.query.filter_by(name=person).first()
        twitter_name = person_info.twitter
        youtube_id = person_info.youtube_id
        instagram_name = person_info.instagram

        posts = []

        job = group([get_instagram.s(instagram_name), 
                    get_twitter.s(twitter_name), 
                    get_youtube.s(youtube_id)])
        result = job.apply_async()
        real_res = result.join()
        instagram_res = real_res[0]
        twitter_res = real_res[1]
        youtube_res = real_res[2]

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

        tabs = ['<li class="nav-tab" id="all" onclick="showAll();">All</li>']   
        if twitter_res:
            tabs.append('<li class="nav-tab" id="twitter" onclick="showTwitter();">Twitter</li>')
        if instagram_res:
            tabs.append('<li class="nav-tab" id="instagram" onclick="showInstagram();">Instagram</li>')
        if youtube_res:
            tabs.append('<li class="nav-tab" id="youtube" onclick="showYoutube();">YouTube</li>')
        
        data = {'embeds': embeds, 'tabs': tabs, 'twitter': twitter_embeds, 'instagram': instagram_embeds, 'youtube': youtube_embeds}

        return render_template('profile.html', form=form, data=data)

    return render_template('profile.html', form=form, data=None)
