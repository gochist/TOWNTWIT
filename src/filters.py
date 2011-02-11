from google.appengine.ext.webapp import template
import re

register = template.create_template_register()

@register.filter
def twit_mention_urlize(txt):
    txt = re.sub("@(\w+)", u"<a href='http://www.twitter.com/\\g<1>'>\\g<0></a>", txt)
    return txt 