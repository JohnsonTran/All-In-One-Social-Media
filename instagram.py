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
embed_url = 'https://graph.facebook.com/v9.0/instagram_oembed'
instagram_url = 'https://www.instagram.com'

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
                cache = {}
                # find the difference from the current instagram and cache
                for i, insta_post in enumerate(insta_posts):
                    post_name = insta_post.find('a')['href']
                    if post_name != latest_cache_post:
                        post_url = instagram_url + post_name
                        # go to the post
                        driver.get(post_url)
                        # check if browser got redirected to login page
                        if driver.current_url == login_url:
                            login()
                            driver.get(post_url)

                        # get the embed for the post
                        params = {'url': post_url, 'access_token': access_token, 'omitscript': 'true'}
                        embed = requests.get(embed_url, params).json()['html']
                        
                        time_posted = driver.find_element_by_xpath("//time[@class='_1o9PC Nzb55']").get_attribute('datetime')
                        time_posted = normalize_datetime(time_posted)

                        post = (time_posted, embed)
                        posts.append(post)
                        cache[i] = {time_posted: post_name}
                    else:
                        break
                # add the rest of the cache
                for cache_post in firebase_cache:
                    post_name = list(cache_post.values())[0]
                    post_url = instagram_url + post_name

                    # get the embed for the post
                    params = {'url': post_url, 'access_token': access_token, 'omitscript': 'true'}
                    embed = requests.get(embed_url, params).json()['html']

                    post = (list(cache_post.keys())[0], embed)
                    posts.append(post)
                    cache[i] = {list(cache_post.keys())[0]: post_name}
                    i += 1
                firebase_app.put('/users/', f'{acct_name}', {'latest': cache})
        else:
            # get the latest 12 posts on a profile
            insta_posts = soup.find_all(class_='v1Nh3 kIKUG _bz0w')
            cache = {}
            for i, insta_post in enumerate(insta_posts):
                post_name = insta_post.find('a')['href']
                post_url = instagram_url + post_name
                # go to the post
                driver.get(post_url)
                # check if browser got redirected to login page
                if driver.current_url == login_url:
                    login()
                    driver.get(post_url)
                
                # get the embed for the post
                params = {'url': post_url, 'access_token': access_token, 'omitscript': 'true'}
                
                embed = requests.get(embed_url, params).json()['html']
                
                time_posted = driver.find_element_by_xpath("//time[@class='_1o9PC Nzb55']").get_attribute('datetime')
                time_posted = normalize_datetime(time_posted)

                post = (time_posted, embed)
                posts.append(post)
                cache[i] = {time_posted: post_name}
            firebase_app.put('/users/', f'{acct_name}', {'latest': cache})
    
    return posts
