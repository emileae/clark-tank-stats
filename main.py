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

@app.route('/sales', methods=['POST'])
def game_sales():
    req_json = request.get_json()
    platform = req_json["platform"]
    link = req_json["link"]
    steamid = req_json["steamid"]
    salesd1 = req_json["salesd1"]
    salesw1 = req_json["salesw1"]
    salesm1 = req_json["salesm1"]
    salesy1 = req_json["salesy1"]
    contact = req_json["contact"]

    salesstats = model.SalesStats()
    salesstats.platform = platform
    salesstats.link = link
    salesstats.steamid = steamid
    salesstats.salesd1 = salesd1
    salesstats.salesw1 = salesw1
    salesstats.salesm1 = salesm1
    salesstats.salesy1 = salesy1
    salesstats.contact = contact
    salesstats.put()
    return "success"

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
    time_unix = []
    followers = []
    reviews = []
    sentiment = []
    perc = []
    for item in items:
        time.append(item.time.strftime('%H:%M %m/%d/%Y'))
        time_unix.append((item.time - datetime.datetime(1970,1,1)).total_seconds())
        followers.append(item.followers)
        reviews.append(item.reviews)
        sentiment.append(item.sentiment)
        perc.append(item.perc)
    
    parsed_items["time"] = time
    parsed_items["time_unix"] = time_unix
    parsed_items["followers"] = followers
    parsed_items["reviews"] = reviews
    parsed_items["sentiment"] = sentiment
    parsed_items["perc"] = perc

    game_json = {
        "created": game_data.created.strftime('%H:%M %m/%d/%Y'),
        "created_unix": (game_data.created - datetime.datetime(1970,1,1)).total_seconds()
    }

    if game_data.released_datetime:
        game_json["released"] = (game_data.released_datetime - datetime.datetime(1970,1,1)).total_seconds()


    return render_template("trend.html", items=json.dumps(parsed_items), game_data=game_data, game_json=json.dumps(game_json))

@app.route('/cron/update_games')
def cron_update_games():
    task = taskqueue.add(
        url='/update_games_task'
    )
    return "success"

@app.route('/cron/update_top_games')
def cron_update_top_games():
    task = taskqueue.add(
        url='/update_top_1000'
    )
    return "success"

@app.route('/update_games_task', methods=['POST'])
def update_games_task():
    get_new_releases()
    return "success"

@app.route('/update_top_1000', methods=['POST'])
def update_top_1000():
    update_top_reviewed()
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
                try:
                    released = released[0].contents[0]
                except:
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

def update_top_reviewed():
    results = []
    
    items = model.Data.query().order(-model.Data.reviews).fetch(100)

    for item in items:
        followers = get_steam_followers(item.steam_id)

        try:

            r = requests.get('https://store.steampowered.com/app/%s' % item.steam_id, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            sentiment = soup.select(".user_reviews_summary_row .game_review_summary")
            if len(sentiment) > 0:
                sentiment = str(sentiment[0].contents[0])
            else:
                sentiment = item.sentiment

            perc = soup.select(".user_reviews_summary_row .responsive_reviewdesc")
            if len(perc) > 0:
                try:
                    perc = str(perc[0].contents[0])
                    rest = perc.split("%")[0]
                    rest2 = perc.split("%")[1]
                    perc = int( re.sub('[^0-9,]', "", rest) )
                    reviews = int( re.sub('[^0-9,]', "", rest2).replace(",", "") )
                except:
                    perc = item.perc
                    reviews = item.reviews
                    print("failed to update perc & reviews %s " % item.steam_id)
            else:
                perc = item.perc
            
            released = soup.select(".user_reviews .release_date .date")
            if len(released) > 0:
                try:
                    released = str(released[0].contents[0])
                except:
                    released = item.released
            else:
                released = item.released

            obj = {
                "steam_id": item.steam_id,
                "title": item.title,
                "released": released,
                "reviews": reviews,
                "sentiment": sentiment,
                "perc": perc,
                "followers": followers,
                "thumb_url": item.thumb_url,
                "new_release": False,
                "top_seller": False
            }

            results.append(obj)

            save_steam_obj(item.steam_id, obj)
        
        except:
            continue

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

