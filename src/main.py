import os
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

# =========
# Constants
# =========
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
    
    def set_twit_token(self, key, secret, is_access):
        token = Token(
            token_key=key,
            token_secret=secret,
            is_access_token=is_access
        )
        token.put()
        
        if self.twit_token:
            self.twit_token.delete()
        
        self.twit_token = token
        self.put()
    
    def set_town_token(self, key, secret, is_access):
        token = Token(
            token_key=key,
            token_secret=secret,
            is_access_token=is_access
        )
        token.put()
        
        if self.town_token:
            self.town_token.delete()
        
        self.town_token = token
        self.put()
            
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
        town_user = None
        twit_user = None

        town_token = user_model.town_token
        twit_token = user_model.twit_token
        
        if town_token and town_token.is_access_token:
            resp, content = signget(
                TOWN_SERVICE,
                town_token.to_oauth2(),
                TOWN_SERVICE['service_provider_url'] + "/1/users/show"
            )
            if resp['status'] == '200': 
                town_user = json.loads(content)
        
        if twit_token and twit_token.is_access_token:
            user_id = twit_token.token_key.split('-')[0]
            api = "/1/users/show.json?user_id=" + user_id
            result = urlfetch.fetch(TWIT_SERVICE['service_provider_url'] + api)
            if result.status_code == 200:
                twit_user = json.loads(result.content)
        
        params = {
            'user': user_model,
            'logout_url': users.create_logout_url("/"),
            'town_user': town_user,
            'twit_user': twit_user
        }
        
        filepath = os.path.join(os.path.dirname(__file__), 'template/index.tpl')
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
            key=result['oauth_token'],
            secret=result['oauth_token_secret'],
            is_access=False
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
        user_model.town_token.token_key = result['oauth_token']
        user_model.town_token.token_secret = result['oauth_token_secret']
        user_model.town_token.is_access_token = True
        user_model.town_token.put()
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
            key=result['oauth_token'],
            secret=result['oauth_token_secret'],
            is_access=False
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
        user_model.twit_token.token_key = result['oauth_token']
        user_model.twit_token.token_secret = result['oauth_token_secret']
        user_model.twit_token.is_access_token = True
        user_model.twit_token.put()
        self.redirect('/')     

class TaskPage(webapp.RequestHandler):
    def post(self):
        user_key = self.request.get('user_key')
        user_model = UserModel.get(user_key)
        # TODO: twit!

        
class TaskTriggerPage(webapp.RequestHandler):
    def get(self):
        # TODO: filter, order
        for user in UserModel.all():
            params = {'user_key':user.key}
            taskqueue.add(url='/task', params=params)
            
# ====
# WSGI 
# ====            
application = webapp.WSGIApplication([
        ('/', MainPage),
        ('/town_auth', TownAuthPage),
        ('/town_callback', TownCallbackPage),
        ('/twit_auth', TwitAuthPage),
        ('/twit_callback', TwitCallbackPage),
        ('/task', TaskPage),
        ('/task_trigger', TaskTriggerPage)
    ],
    debug=True
)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
