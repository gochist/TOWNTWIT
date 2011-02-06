import oauth2
from oauth2 import httplib2, parse_qsl
from urlparse import urlparse

class ClientBase(oauth2.Client):
    callback = None

    def set_callback(self, callback):
        """Callback URL must be registered when request a 'request token'. 
        If the client is not web service, callback can be set to 'oob'(out of 
        band) so that it can follow PIN flow. 
        """
        self.callback = callback

    def request(self, uri, method="GET", body=None, headers=None,
                redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                connection_type=None):
        """This function calls httplib2.request after signing request with oauth.
        Parameters used in this function is exactly same with httplib2.request.
        """

        DEFAULT_CONTENT_TYPE = 'application/x-www-form-urlencoded'

        if not isinstance(headers, dict):
            headers = {}
      
        is_multipart = method == 'POST' and \
                       headers.get('Content-Type', DEFAULT_CONTENT_TYPE) != \
                       DEFAULT_CONTENT_TYPE

        if body and method == 'POST' and not is_multipart:
            parameters = dict(parse_qsl(body))
            if self.callback: 
                parameters['oauth_callback'] = self.callback
        else:
            parameters = {}
            if self.callback: 
                parameters['oauth_callback'] = self.callback

        req = oauth2.Request.from_consumer_and_token(self.consumer,
                                                     token=self.token,
                                                     http_method=method,
                                                     http_url=uri,
                                                     parameters=parameters)
        
        req.sign_request(self.method, self.consumer, self.token)

        if method == "POST":
            headers['Content-Type'] = headers.get('Content-Type',
                                                 DEFAULT_CONTENT_TYPE)
            if is_multipart:
                headers.update(req.to_header())
            else:
                body = req.to_postdata()

        elif method == "GET":
            uri = req.to_url()
        else:
            headers.update(req.to_header())

        return httplib2.Http.request(self, uri, method=method, body=body,
                                     headers=headers,
                                     redirections=redirections,
                                     connection_type=connection_type)    


