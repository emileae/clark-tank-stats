#  to vendor libs into lib folder using requirements.txt: "pip install -t lib -r requirements.txt"

import os
import logging
import json
from flask import Flask, render_template, request, jsonify, redirect
from flask_cors import CORS
import requests
import datetime
import time
import re
from bs4 import BeautifulSoup

# Google libs
from google.appengine.api import taskqueue
from google.appengine.ext import ndb
from google.appengine.datastore.datastore_query import Cursor

# models
import model

import requests_toolbelt.adapters.appengine
requests_toolbelt.adapters.appengine.monkeypatch()

app = Flask(__name__)
CORS(app)# currently this allows all origins access to the API


# ======================================================
#  ROUTING
# ======================================================

@app.route('/')
def home():
    q = request.args.get('q')
    if q == "released":
        items = model.Data.query().order(-model.Data.released_datetime)
    elif q == "reviews":
        items = model.Data.query().order(-model.Data.reviews)
    elif q == "followers":
        items = model.Data.query().order(-model.Data.followers)
    else:
        items = model.Data.query().order(-model.Data.followers)
    return render_template("index.html", items=items)

@app.route('/trend/<steam_id>')
def trend(steam_id):
    q = request.args.get('q')
    game_data = model.Data.query(model.Data.steam_id == steam_id).get()
    items = model.FollowersOverTime.query(model.FollowersOverTime.steam_id == steam_id).order(model.FollowersOverTime.time).fetch(600)
    
    parsed_items = {}
    time = []
    followers = []
    reviews = []
    sentiment = []
    perc = []
    for item in items:
        time.append(item.time.strftime('%H:%M %m/%d/%Y'))
        followers.append(item.followers)
        reviews.append(item.reviews)
        sentiment.append(item.sentiment)
        perc.append(item.perc)
    
    parsed_items["time"] = time
    parsed_items["followers"] = followers
    parsed_items["reviews"] = reviews
    parsed_items["sentiment"] = sentiment
    parsed_items["perc"] = perc

    return render_template("trend.html", items=json.dumps(parsed_items), game_data=game_data)

@app.route('/cron/update_games')
def cron_update_games():
    task = taskqueue.add(
        url='/update_games_task'
    )
    return "success"

@app.route('/update_games_task', methods=['POST'])
def update_games_task():
    get_new_releases()
    # get_top_sellers()
    return "success"

def get_new_releases():
    results = []
    pages = ["1", "2", "3", "4"]
    for page in pages:
        r = requests.get('https://store.steampowered.com/search/?sort_by=Released_DESC&ignore_preferences=1&page=%s' % page)
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.select(".search_result_row")
        for row in rows:
            href = row["href"]
            href = href.replace("https://store.steampowered.com/app/", "")
            href = href.split("/")
            released = row.select(".search_released")
            if released:
                released = released[0].contents[0]
            else:
                released = "-"
            steam_id = href[0]
            title = row.select(".search_name .title")
            title = title[0].contents[0]

            img = row.select(".search_capsule img")
            thumb_url = ""
            if img:
                if img[0]["src"]:
                    thumb_url = img[0]["src"]

            reviews = row.select(".search_reviewscore .search_review_summary")
            sentiment = "-"
            perc = 0
            if len(reviews) > 0:
                reviews = reviews[0]["data-tooltip-html"]
                sentiment = reviews.split("<br>")[0]
                perc = reviews.split("%")[0]
                perc = int( perc.split("<br>")[1] )
                rest = reviews.split("%")[1]
                reviews = int( re.sub('[^0-9,]', "", rest).replace(",", "") )
            else:
                reviews = 0

            followers = get_steam_followers(steam_id)

            obj = {
                "steam_id": steam_id,
                "title": title,
                "released": released,
                "reviews": reviews,
                "sentiment": sentiment,
                "perc": perc,
                "followers": followers,
                "thumb_url": thumb_url,
                "new_release": True,
                "top_seller": False
            }

            results.append(obj)

            save_steam_obj(steam_id, obj)
    return results

def get_top_sellers():
    results = []
    pages = ["1", "2", "3", "4"]
    for page in pages:
        r = requests.get('https://store.steampowered.com/search/?filter=topsellers&ignore_preferences=1&page=%s' % page)
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.select(".search_result_row")
        for row in rows:
            href = row["href"]
            href = href.replace("https://store.steampowered.com/app/", "")
            href = href.split("/")
            released = row.select(".search_released")
            if len(released) > 0:
                if len(released[0].contents) > 0:
                    released = released[0].contents[0]
                else:
                    released = "-"
            else:
                released = "-"
            steam_id = href[0]
            title = row.select(".search_name .title")
            title = title[0].contents[0]

            img = row.select(".search_capsule img")
            thumb_url = ""
            if img:
                if img[0]["src"]:
                    thumb_url = img[0]["src"].split("?")[0]

            reviews = row.select(".search_reviewscore .search_review_summary")
            sentiment = "-"
            perc = 0
            if len(reviews) > 0:
                reviews = reviews[0]["data-tooltip-html"]
                sentiment = reviews.split("<br>")[0]
                perc = reviews.split("%")[0]
                perc = int( perc.split("<br>")[1] )
                rest = reviews.split("%")[1]
                reviews = int( re.sub('[^0-9,]', "", rest).replace(",", "") )
            else:
                reviews = 0

            followers = get_steam_followers(steam_id)

            obj = {
                "steam_id": steam_id,
                "title": title,
                "released": released,
                "reviews": reviews,
                "sentiment": sentiment,
                "perc": perc,
                "followers": followers,
                "thumb_url": thumb_url,
                "new_release": False,
                "top_seller": True
            }

            results.append(obj)

            save_steam_obj(steam_id, obj)
    return results

def get_steam_followers(steam_id):
    r = requests.get('https://steamcommunity.com/games/%s' % steam_id)
    soup = BeautifulSoup(r.text, 'html.parser')
    links = soup.select('#profileBlock .linkStandard')
    followers = 0
    for l in links:
        contents = l.contents[0]
        if "Members" in contents:
            string_num = contents.split(" ")[0]
            string_num = string_num.replace(",", "")
            followers = int(string_num)
    return followers
            


def save_steam_obj(steam_id, obj):
    data = model.Data.query(model.Data.steam_id == steam_id).get()
    if not data:
        data = model.Data()

    data.steam_id = obj["steam_id"]
    data.title = obj["title"]
    data.released = obj["released"]
    if len(obj["released"]) > 0:
        try:
            try:
                data.released_datetime = datetime.datetime.strptime(obj["released"], '%b %d, %Y')
                # print("invalid date:%s - %s"  % ( obj["title"], obj["released"]) )
            except:
                data.released_datetime = datetime.datetime.strptime(obj["released"], '%b %Y')
                # print("invalid date:%s - %s" % ( obj["title"], obj["released"]) )
        except:
            print("invalid date:%s - %s" % ( obj["steam_id"], obj["released"]) )
    data.reviews = obj["reviews"]
    data.sentiment = obj["sentiment"]
    data.perc = obj["perc"]
    data.followers = obj["followers"]
    data.top_seller = obj["top_seller"]
    data.new_release = obj["new_release"]
    data.thumb_url = obj["thumb_url"]
    data.put()

    # create a time series
    followersOverTime = model.FollowersOverTime()

    followersOverTime.steam_id = obj["steam_id"]
    followersOverTime.followers = obj["followers"]
    followersOverTime.reviews = obj["reviews"]
    followersOverTime.sentiment = obj["sentiment"]
    followersOverTime.perc = obj["perc"]

    followersOverTime.put()

