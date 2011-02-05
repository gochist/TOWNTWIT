from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class MainPage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()

        if user:
            params = {
                'nickname': user.nickname(),
                'logout_url': users.create_logout_url("/"),
                'is_admin': users.is_current_user_admin()
            }
            
            self.response.out.write(
                'Hello %(nickname)s <a href="%(logout_url)s">Sign out</a><br>Is administrator: %(is_admin)s' % params
            )
        else:
            self.redirect(users.create_login_url(self.request.uri))
            
application = webapp.WSGIApplication([
        ('/', MainPage),
    ], 
    debug=True
)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()