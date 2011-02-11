#-*- coding:utf-8 -*-
import os
import re
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.api import taskqueue
from google.appengine.api import urlfetch
from django.utils import simplejson as json
from ext import oauth2
from ext import ClientBase
from config import *
from cgi import parse_qsl
from urllib import urlencode
import datetime

# =========
# Constants
# =========
TEMPLATE_ROOT = os.path.join(os.path.dirname(__file__), 'template')

TOWN_CONSUMER = oauth2.Consumer(TOWN_CONSUMER_KEY, TOWN_CONSUMER_SECRET)
TWIT_CONSUMER = oauth2.Consumer(TWIT_CONSUMER_KEY, TWIT_CONSUMER_SECRET)

TOWN_SERVICE = {
    'consumer': TOWN_CONSUMER,
    'callback': TOWN_CALLBACK_URL,
    'request_token_url': TOWN_REQUEST_TOKEN_URL,
    'authorize_url': TOWN_AUTHORIZE_URL,
    'access_token_url': TOWN_REQUEST_TOKEN_URL,
    'service_provider_url': TOWN_SERVICE_PROVIDER_URL
}

TWIT_SERVICE = {
    'consumer': TWIT_CONSUMER,
    'callback': TWIT_CALLBACK_URL,
    'request_token_url': TWIT_REQUEST_TOKEN_URL,
    'authorize_url': TWIT_AUTHORIZE_URL,
    'access_token_url': TWIT_REQUEST_TOKEN_URL,
    'service_provider_url': TWIT_SERVICE_PROVIDER_URL
}

def get_request_token(service):
    client = ClientBase(service['consumer'])
    client.set_callback(service['callback'])
    resp, content = client.request(service['request_token_url'], "POST")
    if resp['status'] != '200':
        raise Exception()
    result = dict(parse_qsl(content))
    return result

def signpost(service, token, uri, body):
    client = ClientBase(service['consumer'], token)
    return client.request(uri, "POST", body)

def signget(service, token, uri):
    client = ClientBase(service['consumer'], token)
    return client.request(uri, "GET")

def get_twit_me(token_model):
    if token_model and token_model.is_access_token:
        user_id = token_model.token_key.split('-')[0]
        api = "/1/users/show.json?user_id=" + user_id
        result = urlfetch.fetch(TWIT_SERVICE['service_provider_url'] + api)
        if result.status_code == 200:
            twit_user = json.loads(result.content)
            return twit_user

def get_town_me(token_model):
    if token_model and token_model.is_access_token:
        resp, content = signget(
            service=TOWN_SERVICE,
            token=token_model.to_oauth2(),
            uri=TOWN_SERVICE_PROVIDER_URL + "/1/users/show"
        )
        if resp['status'] == '200': 
            town_user = json.loads(content)
            if town_user.get('status', 'ok') != 'error':
                return town_user


def post_town_article(user_model, title, message):
    token_model = user_model.town_token
    api = TOWN_SERVICE_PROVIDER_URL + "/1/articles/create/" + user_model.town_board_id
    body_dict = {
        'title': title,
        'message': message
    }
    
    body = urlencode(body_dict, True)
    if token_model and token_model.is_access_token:
        resp, content = signpost(
            service=TOWN_SERVICE,
            token=token_model.to_oauth2(),
            uri=api,
            body=body
        )
        
        if resp['status'] == '200':
            result = json.loads(content)
            if result.get('status', 'ok') != 'error':
                return result

def get_twit_user_timeline(token_model, count=5, since_id=None):
    if token_model and token_model.is_access_token:
        user_id = token_model.token_key.split('-')[0]
        api = TWIT_SERVICE_PROVIDER_URL + "/1/statuses/user_timeline.json?user_id=" + user_id
        if count:
            api = api + "&count=" + str(count)
        if since_id:
            api = api + "&since_id=" + str(since_id)
        result = urlfetch.fetch(api)
        if result.status_code == 200:
            user_timeline = json.loads(result.content)
            return user_timeline

def get_twit_statuses_show(token_model, id):
    if id and token_model and token_model.is_access_token:
        api = TWIT_SERVICE_PROVIDER_URL + "/1/statuses/show/%d.json" % id
        result = urlfetch.fetch(api)
        if result.status_code == 200:
            status = json.loads(result.content)
            return status

def to_town_title(txt):
    re_mention = re.compile("@(\w+)")
    txt = re_mention.sub(u"", txt)
    txt = u"[TWIT] " + (u" ".join(txt.strip().split())[:30] or u"no title")
    return txt.encode('utf8')

# ======
# Filter
# ======  
template.register_template_library('filters')
        

# ======
# Models
# ======
class Token(db.Model):
    token_key = db.StringProperty(required=True)
    token_secret = db.StringProperty(required=True)
    is_access_token = db.BooleanProperty(default=False)
    
    @classmethod
    def get_by_token_key(cls, key):
        models = cls.all().filter('token_key =', key)
        if models.count() > 0:
            return models[0]
        
    def to_oauth2(self):
        return oauth2.Token(self.token_key, self.token_secret)

    def __str__(self):
        return ", ".join((self.token_key, self.token_secret))
    
class UserModel(db.Model):
    user = db.UserProperty(required=True)
    town_token = db.ReferenceProperty(Token, collection_name='town_token')
    twit_token = db.ReferenceProperty(Token, collection_name='twit_token')
    last_twit_id = db.IntegerProperty()
    town_board_id = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    processed = db.DateTimeProperty(auto_now_add=True)
    
    @classmethod
    def get_or_new(cls, user):
        models = cls.all().filter('user =', user)
        if models.count() <= 0:
            model = cls(user=user)
            model.put()
        else:
            model = models[0]
        return model
    
    def set_twit_token(self, token):
        if self.twit_token:
            self.twit_token.delete()
        token.put()
        self.twit_token = token
        self.put()
    
    def set_town_token(self, token):
        if self.town_token:
            self.town_token.delete()
        token.put()
        self.town_token = token
        self.put()

    def update_last_twit_id(self, id):
        self.last_twit_id = id
        self.put()
        
    def update_processed(self):
        self.processed = datetime.datetime.now()
        self.put()
    
    def have_twit_access_token(self):
        return self.twit_token and self.twit_token.is_access_token
    
    def have_town_access_token(self):
        return self.town_token and self.town_token.is_access_token
    
    def refresh_last_twit_id(self):
        if self.have_twit_access_token():
            timeline = get_twit_user_timeline(self.twit_token, 1)
            if timeline:
                self.update_last_twit_id(timeline[0]['id'])
                
    def queue_to_twit(self):
        self.update_processed()
        if self.have_twit_access_token() and self.have_town_access_token():
            params = {'user_key':self.key()}
            taskqueue.add(url='/task', params=params, retry_options=None)

            
# ========
# Handlers
# ========        
class MainPage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return

        user_model = UserModel.get_or_new(user)
        twit_user = get_twit_me(user_model.twit_token)
        last_twit = get_twit_statuses_show(
            token_model=user_model.twit_token,
            id=user_model.last_twit_id
        )
                
        params = {
            'user': user_model,
            'logout_url': users.create_logout_url("/"),
            'town_user': get_town_me(user_model.town_token),
            'twit_user': twit_user,
            'last_twit': last_twit
        }

        filepath = os.path.join(TEMPLATE_ROOT, 'index.tpl')
        self.response.out.write(template.render(filepath, params))

class TownAuthPage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return

        result = get_request_token(TOWN_SERVICE) 
        user_model = UserModel.get_or_new(user)
        user_model.set_town_token(
            Token(
                token_key=result['oauth_token'],
                token_secret=result['oauth_token_secret'],
                is_access_token=False
            )
        )
        
        self.redirect(TOWN_AUTHORIZE_URL + "?oauth_token=" + result['oauth_token'])


class TownCallbackPage(webapp.RequestHandler):
    consumer = oauth2.Consumer(TOWN_CONSUMER_KEY, TOWN_CONSUMER_SECRET)
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return    

        oauth_token = self.request.get('oauth_token')
        oauth_verifier = self.request.get('oauth_verifier')

        user_model = UserModel.get_or_new(user)
        if user_model.town_token.token_key != oauth_token:
            raise Exception()
        
        token = user_model.town_token.to_oauth2()
        token.set_verifier(oauth_verifier)
        client = ClientBase(self.consumer, token)
        resp, content = client.request(TOWN_ACCESS_TOKEN_URL, "POST")
        if resp['status'] != '200':
            raise Exception()
        result = dict(parse_qsl(content))
        user_model.set_town_token(
            Token(
                  token_key=result['oauth_token'],
                  token_secret=result['oauth_token_secret'],
                  is_access_token=True
            )
        )
        
        me = get_town_me(user_model.town_token)
        if me:
            entrance_year = (me['entrance_year'] % 100)
            user_model.town_board_id = "board_alumni%02d" % entrance_year 
            user_model.put()
        
        self.redirect('/')
        
class TownTokenDeletePage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return
        
        user_model = UserModel.get_or_new(user)
        if user_model.town_token:
            user_model.town_token.delete()
            user_model.town_token = None
            user_model.put()            
        
        self.redirect('/')
        
class TwitTokenDeletePage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return
        
        user_model = UserModel.get_or_new(user)
        if user_model.twit_token:
            user_model.twit_token.delete()
            user_model.twit_token = None
            user_model.put()
        
        self.redirect('/')

class TwitAuthPage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return

        result = get_request_token(TWIT_SERVICE) 
        user_model = UserModel.get_or_new(user)
        user_model.set_twit_token(
            Token(
                token_key=result['oauth_token'],
                token_secret=result['oauth_token_secret'],
                is_access_token=False
            )
        )
        
        self.redirect(TWIT_AUTHORIZE_URL + "?oauth_token=" + result['oauth_token'])
        

class TwitCallbackPage(webapp.RequestHandler):
    consumer = oauth2.Consumer(TWIT_CONSUMER_KEY, TWIT_CONSUMER_SECRET)
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return    

        oauth_token = self.request.get('oauth_token')
        oauth_verifier = self.request.get('oauth_verifier')

        user_model = UserModel.get_or_new(user)
        if user_model.twit_token.token_key != oauth_token:
            raise Exception()
        
        token = user_model.twit_token.to_oauth2()
        token.set_verifier(oauth_verifier)
        client = ClientBase(self.consumer, token)
        resp, content = client.request(TWIT_ACCESS_TOKEN_URL, "POST")
        if resp['status'] != '200':
            raise Exception()
        result = dict(parse_qsl(content))
        user_model.set_twit_token(
            Token(
                  token_key=result['oauth_token'],
                  token_secret=result['oauth_token_secret'],
                  is_access_token=True
            )
        )
        
        user_model.refresh_last_twit_id()
        user_model.update_processed()

        self.redirect('/')     

class TaskPage(webapp.RequestHandler):        
    def post(self):
        user_key = self.request.get('user_key')
        user_model = UserModel.get(user_key)

        if user_model.last_twit_id == None:
            user_model.refresh_last_twit_id()
            return
        
        twit_timeline = get_twit_user_timeline(
            token_model=user_model.twit_token,
            count=5,
            since_id=user_model.last_twit_id
        )
        
        if twit_timeline:
            for twit in reversed(twit_timeline):
                # backup and update last_twit_id
                last_twit_id = user_model.last_twit_id
                user_model.update_last_twit_id(twit['id'])
                
                # skip reply
                if twit['in_reply_to_status_id']:
                    continue

                # build message from twit
                message = template.render(
                    os.path.join(TEMPLATE_ROOT, 'twit.tpl'),
                    {'twit':twit}
                )
                
                # post twit to town
                ret = post_town_article(
                    user_model=user_model,
                    title=to_town_title(twit['text']),
                    message=message
                )
                
                # posting to town failed 
                if not ret:
                    user_model.update_last_twit_id(last_twit_id)
        
class TaskTriggerPage(webapp.RequestHandler):
    def get(self):
        users = UserModel.all().order('processed')
        bucket = users.count() / 3 + 1
        for user in users.fetch(bucket):
            user.queue_to_twit()

            
# ====
# WSGI 
# ====            
def main():
    urls = [
        ('/', MainPage),
        ('/town_auth', TownAuthPage),
        ('/town_callback', TownCallbackPage),
        ('/towntoken/delete', TownTokenDeletePage),
        ('/twit_auth', TwitAuthPage),
        ('/twit_callback', TwitCallbackPage),
        ('/twittoken/delete', TwitTokenDeletePage),
        ('/task', TaskPage),
        ('/task_trigger', TaskTriggerPage)
    ]
    application = webapp.WSGIApplication(urls, debug=True)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
