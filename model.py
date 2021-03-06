from google.appengine.ext import ndb

class Data(ndb.Model):
    steam_id = ndb.StringProperty(required=True)
    title = ndb.StringProperty()
    followers = ndb.IntegerProperty()
    released = ndb.StringProperty()
    released_datetime = ndb.DateTimeProperty()
    reviews = ndb.IntegerProperty()
    sentiment = ndb.StringProperty()
    perc = ndb.IntegerProperty()
    top_seller = ndb.BooleanProperty()
    new_release = ndb.BooleanProperty()
    thumb_url = ndb.StringProperty()
    last_updated = ndb.DateTimeProperty(auto_now=True)
    created = ndb.DateTimeProperty(auto_now_add=True)

class FollowersOverTime(ndb.Model):
    steam_id = ndb.StringProperty(required=True)
    time = ndb.DateTimeProperty(auto_now=True)
    followers = ndb.IntegerProperty()
    reviews = ndb.IntegerProperty()
    sentiment = ndb.StringProperty()
    perc = ndb.IntegerProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)

class SalesStats(ndb.Model):
    platform = ndb.StringProperty()
    link = ndb.StringProperty()
    steamid = ndb.StringProperty()
    salesd1 = ndb.StringProperty()
    salesw1 = ndb.StringProperty()
    salesm1 = ndb.StringProperty()
    salesy1 = ndb.StringProperty()
    contact = ndb.StringProperty()
    verified = ndb.BooleanProperty(default=False)
    created = ndb.DateTimeProperty(auto_now_add=True)

