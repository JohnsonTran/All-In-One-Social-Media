import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from os import environ
from dotenv import load_dotenv, find_dotenv

from post import Post
from firebase import firebase

from datetime import datetime
import time

load_dotenv(find_dotenv())

firebase_app = firebase.FirebaseApplication(environ.get('FIREBASE_URL'), None)

# set up Chrome driver
options = Options()
options.add_argument('--window-size=1920,1080')
options.add_argument('--ignore-certificate-errors')
options.add_argument('--allow-running-insecure-content')
options.add_argument('--headless')
# used for websites that block headless mode
user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36'
options.add_argument(f'user-agent={user_agent}')
driver = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=options)

access_token = environ.get('INSTAGRAM_APP_ID') + '|' + environ.get('INSTAGRAM_CLIENT_ID')

login_url = 'https://www.instagram.com/accounts/login/'
instagram_url = 'https://www.instagram.com'
embed_url = 'https://graph.facebook.com/v9.0/instagram_oembed'

# get rid of the '.' in the date time so it can be put into Firebase
def normalize_datetime(time_posted):
    date_time = time_posted.split('T')
    date_time[1] = date_time[1][:date_time[1].index('.')]
    time_posted = ' '.join(date_time)
    return time_posted

def login():
    # wait for the login page to load
    wait = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, 'username'))
    )
    # log in with account information
    username = driver.find_element_by_name('username')
    username.send_keys(environ.get('INSTAGRAM_USERNAME'))
    password = driver.find_element_by_name('password')
    password.send_keys(environ.get('INSTAGRAM_PASSWORD'))
    login_button = driver.find_element_by_xpath("//div[contains(text(), 'Log In')]")
    login_button.click()
    # wait for log in to complete
    wait = WebDriverWait(driver, 10).until(EC.staleness_of(username))

# get a specified number of posts on an instagram page and make a cache of the posts for firebase
def get_posts_and_cache(insta_posts, cache, num=12):
    posts = []
    for i in range(num):
        post_name = insta_posts[i].find('a')['href']
        post_url = instagram_url + post_name
        # go to the post
        driver.get(post_url)
        
        # get the embed for the post
        params = {'url': post_url, 'access_token': access_token, 'omitscript': 'true'}
        embed = requests.get(embed_url, params).json()['html']
        
        time_posted = driver.find_element_by_xpath("//time[@class='_1o9PC Nzb55']").get_attribute('datetime')
        time_posted = normalize_datetime(time_posted)

        post = (time_posted, embed)
        posts.append(post)
        cache[i] = {time_posted: post_name}
    return posts

def get_instagram_embed_and_time(acct_name):
    posts = []
    if acct_name:
        acct_url = f'https://www.instagram.com/{acct_name}/'

        driver.get(acct_url)
        # check if browser got redirected to login page
        if driver.current_url == login_url:
            login()
            driver.get(acct_url)

        soup = BeautifulSoup(driver.page_source, 'lxml')
        res = firebase_app.get(f'/users/{acct_name}', None)
        cache = {}
        # get cache for users that exist in the database
        if res != None:
            # ping latest insta post - no change: grab from cache, else: pull again and change
            insta_posts = soup.find_all(class_='v1Nh3 kIKUG _bz0w')
            firebase_cache = firebase_app.get(f'/users/{acct_name}/latest/', None)
            latest_cache_post = list(firebase_cache[0].values())[0]
            latest_insta = insta_posts[0].find('a')['href']
            # check if a new post has been posted since the last data pull
            if latest_cache_post == latest_insta:
                for cache_post in firebase_cache:
                    post_name = list(cache_post.values())[0]
                    post_url = instagram_url + post_name

                    # get the embed for the post
                    params = {'url': post_url, 'access_token': access_token, 'omitscript': 'true'}
                    embed = requests.get(embed_url, params).json()['html']

                    post = (list(cache_post.keys())[0], embed)
                    posts.append(post)
            # get the new posts on the profile and update the cache
            else:
                # find the difference from the current instagram and cache
                diff = 0
                for insta_post in insta_posts:
                    post_name = insta_post.find('a')['href']
                    if post_name != latest_cache_post:
                        break
                    diff += 1
                posts = get_posts_and_cache(insta_posts, cache, diff)

                # add the rest of the cache
                i = 0
                while diff < 12:
                    post_name = list(firebase_cache[i].values())[0]
                    post_url = instagram_url + post_name

                    # get the embed for the post
                    params = {'url': post_url, 'access_token': access_token, 'omitscript': 'true'}
                    embed = requests.get(embed_url, params).json()['html']

                    post = (list(cache_post.keys())[0], embed)
                    posts.append(post)
                    cache[diff] = {list(cache_post.keys())[0]: post_name}
                    i += 1
                    diff += 1
                firebase_app.put('/users/', f'{acct_name}', {'latest': cache})
        # user doesn't exist in the database
        else:
            # get the latest 12 posts on a profile
            insta_posts = soup.find_all(class_='v1Nh3 kIKUG _bz0w')
            posts = get_posts_and_cache(insta_posts, cache)
            firebase_app.put('/users/', f'{acct_name}', {'latest': cache})
    
    return posts

# get at most 180 posts from an instagram page to cache for infinite scroll
def get_instagram_posts(acct_name):
    posts = []
    if acct_name:
        acct_url = f'https://www.instagram.com/{acct_name}/'

        driver.get(acct_url)
        # check if browser got redirected to login page
        if driver.current_url == login_url:
            login()
            driver.get(acct_url)

        SCROLL_PAUSE_TIME = 1.5

        # get scroll height
        last_height = driver.execute_script("return document.body.scrollHeight")

        posts = {}
        while True:
            # scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # wait to load page
            time.sleep(SCROLL_PAUSE_TIME)

            # calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

            soup = BeautifulSoup(driver.page_source, 'lxml')

            insta_posts = soup.find_all(class_='v1Nh3 kIKUG _bz0w')
            for insta_post in insta_posts:
                post_name = insta_post.find('a')['href']
                if post_name not in posts:
                    posts[post_name] = None
                    # limit to only 180 posts because of 200 API request limit
                    if len(posts.keys()) >= 180:
                        break
    
    return list(posts.keys())
