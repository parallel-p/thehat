from google.appengine.api import users
import webapp2

from webapp2_extras import jinja2
from webapp2_extras import i18n

from objects.user_devices import get_device_and_user, User, get_user
from google.appengine.api.app_identity import get_application_id
from google.appengine.ext import ndb
from handlers.service.notifications import NotificationChannel

__author__ = 'nikolay'


class GenericHandler(webapp2.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(GenericHandler, self).__init__(*args, **kwargs)


class WebRequestHandler(GenericHandler):
    user_key = None
    user = None

    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)

    def dispatch(self):
        self.user = users.get_current_user()
        if self.user is None:
            if self.login_required:
                self.redirect(users.create_login_url(self.request.url))
                return
        else:
            self.user_key = (User.query(User.user_id == self.user.user_id()).get(keys_only=True) or
                             User(user_id=self.user.user_id(), user_object=self.user).put())
        webapp2.RequestHandler.dispatch(self)

    def draw_page(self, template_name, **render_data):
        dev = "the-hat-international" == get_application_id()
        template = self.jinja2().environment.get_template('{}.html'.format(template_name))
        render_data['dev'] = dev
        render_data['user_link'] = (users.create_logout_url('/') if self.user
                                    else users.create_login_url(self.request.url))
        if self.user:
            render_data['user_email'] = users.get_current_user().email()
        else:
            render_data['user_email'] = None
        render_data['is_admin'] = users.is_current_user_admin()
        curr_channel = ndb.Key(NotificationChannel,
                               "notifications").get()
        render_data['token'] = curr_channel.channel_token if curr_channel else None

        if self.user:
            locale = self.user_key.get().localization
        else:
            locale = 'en_US'

        i18n.get_i18n().set_locale(locale)

        self.response.write(template.render(render_data))

    def __init__(self, *args, **kwargs):
        self.login_required = False
        super(WebRequestHandler, self).__init__(*args, **kwargs)


class AdminRequestHandler(WebRequestHandler):
    def dispatch(self):
        if users.get_current_user() is None:
            self.redirect(users.create_login_url())
        if not users.is_current_user_admin():
            self.redirect('/')
        else:
            WebRequestHandler.dispatch(self)

    def __init__(self, *args, **kwargs):
        super(AdminRequestHandler, self).__init__(*args, **kwargs)
        self.login_required = True


class APIRequestHandler(GenericHandler):
    def __init__(self, *args, **kwargs):
        super(APIRequestHandler, self).__init__(*args, **kwargs)


class AuthorizedAPIRequestHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(APIRequestHandler, self).__init__(*args, **kwargs)
        self.device_id = None
        self.device_key = None
        self.user_key = None

    def dispatch(self):
        self.device_id = (self.request.route_kwargs.get('device_id', None) or
                          self.request.headers.get('TheHat-Device-Identity', None))
        if self.device_id is None:
            self.response.headers.add("WWW-Authenticate", "device-id")
            self.abort(401)
        self.device_key, self.user_key = get_device_and_user(self.device_id)
        super(APIRequestHandler, self).dispatch()


class ServiceRequestHandler(GenericHandler):
    def __init__(self, *args, **kwargs):
        super(ServiceRequestHandler, self).__init__(*args, **kwargs)

    def dispatch(self):
        super(ServiceRequestHandler, self).dispatch()