#!/usr/bin/env python
import os
import jinja2
import webapp2
from models import Uporabnik
import datetime
import time
import hashlib
import hmac
import secret
from google.appengine.api import users


template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=False)


class BaseHandler(webapp2.RequestHandler):

    def write(self, *a, **kw):
        return self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        return self.write(self.render_str(template, **kw))

    def render_template(self, view_filename, params=None):
        if not params:
            params = {}

        cookie_value = self.request.cookies.get("uid")

        if cookie_value:
            params["logiran"] = self.preveri_cookie(cookie_vrednost=cookie_value)
        else:
            params["logiran"] = False

        template = jinja_env.get_template(view_filename)
        return self.response.out.write(template.render(params))

    def ustvari_cookie(self, uporabnik):
        uporabnik_id = uporabnik.key.id()
        expires = datetime.datetime.utcnow() + datetime.timedelta(days=10)
        expires_ts = int(time.mktime(expires.timetuple()))
        sifra = hmac.new(str(uporabnik_id), str(secret) + str(expires_ts), hashlib.sha1).hexdigest()
        vrednost = "{0}:{1}:{2}".format(uporabnik_id, sifra, expires_ts)
        self.response.set_cookie(key="uid", value=vrednost, expires=expires)

    def preveri_cookie(self, cookie_vrednost):
        uporabnik_id, sifra, expires_ts = cookie_vrednost.split(":")

        if datetime.datetime.utcfromtimestamp(float(expires_ts)) > datetime.datetime.now():
            preverba = hmac.new(str(uporabnik_id), str(secret) + str(expires_ts), hashlib.sha1).hexdigest()

            if sifra == preverba:
                return True
            else:
                return False
        else:
            return False


class MainHandler(BaseHandler):
    def get(self):
        return self.render_template("hello.html")


class RegistracijaHandler(BaseHandler):
    def get(self):
        self.render_template("registracija.html")

    def post(self):
        ime = self.request.get("ime")
        priimek = self.request.get("priimek")
        email = self.request.get("email")
        geslo = self.request.get("geslo")
        ponovno_geslo = self.request.get("ponovno_geslo")

        mail_obstaja  = Uporabnik.query(Uporabnik.email == email).fetch()

        if mail_obstaja:
            user_exists = True
            params = {"user_exists":user_exists}
            return self.render_template("registracija.html",params=params)
        elif geslo == ponovno_geslo:
            Uporabnik.ustvari(ime=ime, priimek=priimek, email=email, original_geslo=geslo)
            return self.redirect_to('login')


class LoginHandler(BaseHandler):
    def get(self):
        self.render_template("login.html")

    def post(self):
        email = self.request.get("email")
        geslo = self.request.get("geslo")

        uporabnik = Uporabnik.query(Uporabnik.email == email).get()

        if Uporabnik.preveri_geslo(original_geslo=geslo, uporabnik=uporabnik):
            self.ustvari_cookie(uporabnik=uporabnik)
            self.redirect_to("chat")
            return
        else:
            self.redirect_to("chat")
            return

class ChatHandler(BaseHandler):
    def get(self):
        user = users.get_current_user()
        mail = user.email
        params = {"mail":mail}
        self.render_template("chat.html",params=params)


    def post(self):
        a = users.get_current_user()
        b = self.request.get("new_chat")

        params = {"a":a,"b":b}
        return self.render_template("chat.html",params = params)

class TestHandler(BaseHandler):
    def get(self):
        self.render_template("test.html")

app = webapp2.WSGIApplication([
    webapp2.Route('/', MainHandler, name='main'),
    webapp2.Route('/registracija', RegistracijaHandler),
    webapp2.Route('/login', LoginHandler, name='login'),
    webapp2.Route('/chat',ChatHandler, name='chat'),
    webapp2.Route('/test',TestHandler, name='test'),
], debug=True)

