# -*- coding: utf-8 -*-

##############################################################################
# import modules

import os
import sqlite3
import logging
import functools
from Cookie import SimpleCookie
from ConfigParser import ConfigParser
from wsgiref.util import shift_path_info

# @depends: paste, mako

# TODO: paste base, or werkzeug framework
# TODO: class AsyncHTTPServer
# TODO: class Template/TemplateLookup
# TODO: class HTTPExceptionMiddleware
# TODO: /favicon.ico -> redirect to static/favicon.ico
# TODO: use logging

##############################################################################
# Model

# Read ../model/portal.sql
SQL_CREATE_TABLE = """

    CREATE TABLE user_table (
        id INTEGER PRIMARY KEY,
        email VARCHAR UNIQUE,
        password VARCHAR,
        enable BOOLEAN DEFAULT 0,
        lastlogin DATETIME DEFAULT NULL,
        registered DATETIME DEFAULT CURRENT_DATE
    );
    
    CREATE TABLE server_table (
        id INTEGER PRIMARY KEY,
        uid INTEGER,
        address VARCHAR UNIQUE,
        username VARCHAR,
        password VARCHAR,
        url VARCHAR,
        comment VARCHAR,
        enable BOOLEAN DEFAULT 1,
        lastaccess DATETIME,
        registered DATETIME DEFAULT CURRENT_DATE
    );
    
    CREATE TABLE log_table (
        id INTEGER PRIMARY KEY,
        uid INTEGER,
        sender VARCHAR,
        message VARCHAR,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- currently, event_table is not used.
    CREATE TABLE event_table (
        id INTEGER PRIMARY KEY,
        uid INTEGER,
        sid INTEGER,
        message VARCHAR,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

"""

SQL_INSERT_USER = """
    INSERT INTO user_table (email,password) VALUES (?, ?)
"""
SQL_INSERT_SERVER = """
    INSERT INTO server_table (uid,address,username,password,url,comment)
        VALUES (?, ?, ?, ?, ?, ?)
"""
SQL_INSERT_LOG = """
    INSERT INTO log_table (uid,sender,message) VALUES (?, ?, ?)
"""

SQL_SELECT_USER_UID = """
    SELECT id FROM user_table WHERE email = ? AND password = ?
"""

SQL_UPDATE_USER_PASSWORD = """
    UPDATE user_table SET password = ? WHERE id = ? AND password = ?
"""

SQL_UPDATE_SERVER_ENABLE = """
    UPDATE server_table SET enable = ? WHERE uid = ?
"""

##############################################################################

class Database(object):

    # NOTE: self.cloesd flag is not thread safe.

    def __init__(self, dbfile):
        self.connection = connection = sqlite3.connect(dbfile)
        self.cursor = connection.cursor()
        self.closed = False

    def __del__(self):
        if not self.closed:
            self.close()

    def close(self):
        self.cursor.close()
        self.connection.close()
        self.closed = True

    def __getattr__(self, key):
        try:
            return getattr(self.cursor, key)
        except AttributeError:
            return getattr(self.connection, key)

class TableBase(object):
    def __init__(self, db):
        self.db = db

    def select(self):
        self.db.execute('SELECT * FROM %s' % self.table_name)
        return self.db.cursor

class UserTable(TableBase):
    table_name = 'user_table'

    def register(self, email, password):
        self.db.execute(SQL_INSERT_USER, (email,password))

    def change_password(self, uid, oldpassword, newpassword):
        self.db.execute(SQL_UPDATE_USER_PASSWORD, (newpassword,uid,oldpassword))

    def login(self, email, password):
        self.db.execute(SQL_SELECT_USER_UID, (email,password))
        row = self.db.fetchone()
        return row[0] if row else row

class ServerTable(TableBase):
    table_name = 'user_table'

    def register(self, uid, address, username, password, url, comment):
        self.db.execute(SQL_INSERT_SERVER,
            (uid,address,username,password,url,comment))

    def unregister(self, id):
        # TODO: server unregister
        pass

    def change_state(self, uid, state):
        self.db.execute(SQL_UPDATE_SERVER_ENABLE, (state,uid))

class LogTable(TableBase):
    table_name = 'log_table'

    def send(self, uid, sender, message):
        self.db.execute(SQL_INSERT_LOG, (uid,sender,message))

class EventTable(TableBase):
    table_name = 'event_table'


class Model(object):
    def __init__(self, db):
        self.db = db
        self.log = LogTable(db)
        self.user = UserTable(db)
        self.event = EventTable(db)
        self.server = ServerTable(db)

    def create_table(self):
        self.db.executescript(SQL_CREATE_TABLE)

    def commit(self):
        self.db.commit()

##############################################################################
# Utility functions

import string
import random

def _gen_password(length=8, letters=string.letters):
    return ''.join(random.choice(letters) for x in range(length))

mime = {
    '.txt': 'text/plane',
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.png': 'image/png',
    '.jpg': 'image/jpg',
    '.gif': 'image/gif',
    '.ico': 'image/x-icon',
}

compose = lambda funcs,arg: reduce(lambda x,f:f(x), funcs, arg)

class Option(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

##############################################################################
# Configure

class MyConfigParser(ConfigParser):
    def get_section(self, section):
        return self._sections[section]

def load_config(inifile, section='app-config', dict_type=Option):
    ini = MyConfigParser(dict_type=dict_type)
    ini.read(inifile)
    return ini.get_section(section)

##############################################################################
# HTTP Error Response

# TODO: each ErrorResponse instance should return response
# TODO: return view.render("./error/404.html", **environ)
# TODO: adapter to environ,start_response -> request,response

def _unauth(environ, start_response):
    # XXX: realm not passed
    realm = environ['_EXCEPTION'].realm
    start_response('401 Unauthorized',
        [('Content-Type','text/plain'),
         ('WWW-Authenticate','Basic realm="%s"' % realm)
        ])
    yield 'Unauthorized'

def _notfound(environ, start_response):
    start_response('404 Not Found', [('Content-Type','text/plain')])
    yield 'Not found'

def _notimplemented(environ, start_response):
    start_response('501 NotImplemented', [('Content-Type','text/plain')])
    yield 'Not Implemented'

class HTTPErrorResponse(Exception):
    def __init__(self, status, reason=''):
        self.status = status
        self.reason = reason

    # TODO: def __call__(self, environ, start_response):

##############################################################################
# Middleware

class MiddlewareBase(object):
    def __init__(self, app=None):
        self.app = app
        
    def bind(self, app):
        # for lazy-binding app
        self.app = app
        return self

    def __call__(self, environ, start_response):
        raise NotImplementedError


class AuthMiddleware(MiddlewareBase):
    def __init__(self, realm, authfunc, app=None):
        super(AuthMiddleware, self).__init__(app)
        self.realm = realm
        self.authfunc = authfunc

    def authorized(self, auth):
        if not auth:
            return False 
        auth_type, encoded = auth.split(None,1)
        if auth_type.lower() != "basic":
            return False
        username,password = encoded.decode('base64').split(':')
        return self.authfunc(username, password)

    def __call__(self, environ, start_response):
        if not self.authorized(environ.get('HTTP_AUTHORIZATION','')):
            # TODO: raise 401
            start_response('401 Unauthorized',
                [('Content-Type','text/html'),
                 ('WWW-Authenticate', 'Basic realm="%s"' % self.realm)])
            return ["auth page"] # XXX: response page for 401
        else:
            return app(environ, start_response)


# implement this or use Beaker library (session,cache)
class SessionMiddleware(MiddlewareBase):

    key = 'session.data'

    def __init__(self, session_store, app=None):
        super(SessionMiddleware, self).__init__(app)
        self.session_store = session_store

    def __call__(self, environ, start_response):
        cookie = SimpleCookie(environ['HTTP_COOKIE'])
        sid = cookie[self.session_key].value
        if sid:
            environ[self.session_key] = self.store[sid]
        return self.app(environ, start_response)


class HTTPErrorResponseMiddleware(MiddlewareBase):

    error_handlers = {
        401: _unauth,
        404: _notfound,
        501: _notimplemented,
    }
    
    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        except HTTPErrorResponse, e:
            handler = self.error_handlers.get(e.status, _notimplemented)
            environ['_EXCEPTION'] = e
            return handler(environ, start_response)

##############################################################################

# TODO: import cPickle
# TODO: from tempfile import TemporaryFile

class SessionStore(dict):

    def __init__(self, factory=dict):
        self.factory = factory

    def __getitem__(self, key):
        if not key in self:
            self[key] = self.factory()
        return dict.__getitem__(self, key)

##############################################################################
# URI Mapping

def _dict2tuple(data, **kw):
    return ((x,data[x]) for x in sorted(data, **kw))


class URIMapping(object):
    # TODO: move to middleware section

    def __init__(self, mapping):
        self.mapping = list(_dict2tuple(mapping, key=len, reverse=True))

    def __call__(self, environ, start_response):
        path_info = environ['PATH_INFO']
        for path,app in self.mapping:
            if path_info.startswith(path):
                if path.endswith('/'):
                    shift_path_info(environ)
                return app(environ, start_response)
        else:
            raise HTTPErrorResponse(404)


class Site(object):
    # WSGI application base

    def __init__(self, get, post):
        self.get = get
        self.post = post

    def __call__(self, environ, start_response):
        request_method = environ.get('REQUEST_METHOD', None)
        request = HTTPRequest(environ)
        response = HTTPResponse(start_response)

        if request_method == 'GET':
            return self.get(environ, start_response)
        elif request_method == 'POST':
            return self.post(environ, start_response)
        else:
            raise HTTPErrorResponse(501)

class JamFarmPortal(Site):
    pass

##############################################################################

class HTTPRequest(object):
    # TODO: access form data

    def __init__(self, environ):
        self.environ = environ
        
    def __getattr__(self, key):
        key = key.upper()
        if key in self.environ:
            return self.environ[key]
        raise AttributeError, key


class HTTPResponse(dict):
    def __init__(self, start_response, **headers):
        self.start_response = start_response
        self.update_headers(headers)
    
    def update_headers(self, headers):
        assert isinstance(headers, dict)
        for k,v in headers.iteritems():
            self[k.lower()] = v
    
    def start(self, code, state, **headers):
        headers.update(self)
        self.start_response("%d %s" % (code, state), _dict2tuple(headers))

# Transform WSGI method call (environ, start_response) -> (request, response)
def content_handler(func):
    @functools.wraps(func)
    def _wrapped(self, environ, start_response):
        request = HTTPRequest(environ)
        response = HTTPResponse(start_response)
        return func(self, request, response)
    return _wrapped

class ContentBase(object):
    def __init__(self, app):
        self.app = app


##############################################################################
# Request

class require_auth(object):

    # functools.wrap required __name__
    __name__ = 'require_auth'

    def __init__(self, authfunc):
        self.authfunc = authfunc
        
    def __call__(self, self_, request, response):
        # TODO: implement auth mechanism for content handler base
        if not hasattr(request,'auth') or not request.auth:
            raise HTTPErrorResponse(401)
        return self.func(self_, request, response)


##############################################################################
# Response

class View(object):
    def __init__(self, factory):
        self.factory = factory

    def render(self, name, **args):
        template = self.factory.get_template(name)
        return template.render(**args)

##############################################################################
# Contents

class UserContent(ContentBase):
    @content_handler
    def register(self, request, response):
        pass
        
    @content_handler
    def login(self, request, response):
        pass
    
    @content_handler
    def change_password(self, request, response):
        pass

class ServerContent(ContentBase):
    @content_handler
    def register(self, request, response):
        pass
        
    @content_handler
    def update_info(self, request, response):
        pass

class JSONContent(ContentBase):
    @content_handler
    def server_list(self, request, response):
        pass
        
    @content_handler
    def server_info(self, request, response):
        pass

class StaticContent(ContentBase):
    # TODO: spool cache small file ?
    @content_handler
    def __call__(self, request, response):
        path_info = request.path_info
        path = os.path.join(self.app.config.static, path_info.strip('/'))
        if not os.path.isfile(path):
            raise HTTPErrorResponse(404)
        
        content_type = mime.get(os.path.splitext(path_info)[-1])
        response.start(200, 'Ok', **{'Content-Type': content_type})
        return open(path, 'rb')

class IndexContent(ContentBase):
    @content_handler
    def __call__(self, request, response):
        response.start(200, 'Ok', **{'Content-Type': 'text/html'})
        return self.app.view.render(
            'index.html',
            title=self.app.config.site_name,
        )

class SiteContainer(object):
    def __init__(self, model, view, **config):
        self.view = view
        self.model = model
        self.config = Option(config)
        
        self.json = JSONContent(self)
        self.user = UserContent(self)
        self.server = ServerContent(self)
        self.static = StaticContent(self)
        self.index = IndexContent(self)

##############################################################################

# XXX: refactoring URI mapping (separate get/post was not good idea)
def build_app(**config):
    from mako.lookup import TemplateLookup
    
    view = View(TemplateLookup(directories=config['templates'].split(',')))
    model = Model(Database(config['dbfile']))
    site = SiteContainer(model, view, **config)
    
    middleware_chain = [
        HTTPErrorResponseMiddleware,
    ]
    
    get_mapping = URIMapping({
        '/json/server_list': site.json.server_list,
        '/json/server_info': site.json.server_info,
        '/static/': site.static,
        '/': site.index,
    })
    post_mapping = URIMapping({
        '/user/register': site.user.register,
        '/user/login': site.user.login,
        '/user/change_password': site.user.change_password,
        '/server/register': site.server.register,
        '/server/update_info': site.server.update_info,
    })

    app = JamFarmPortal(get_mapping, post_mapping)
    
    return compose(middleware_chain, app)
    

##############################################################################

def init_app_with_config(inifile):
    config = load_config(inifile) if os.path.isfile(inifile) else {}
    return build_app(**config)


def run_server(host='127.0.0.1', port=8000, inifile=None):
    try:
        from paste import reloader
        from paste import httpserver
        from paste.evalexception import EvalException
        reloader.install()
    except ImportError:
        logging.warn('required paste.httpserver and paste.reloader')
    
    app = init_app_with_config(inifile)
    if __debug__:
        app = EvalException(app)
    httpserver.serve(app, host, int(port))


def test_model():
    from contextlib import closing
    from pprint import pprint

    with closing(Database(':memory:')) as db:
        
        model = Model(db)
        model.create_table()
        model.user.register("tea@hotmail.com", "xxx")
        
        # sqlite3.IntegrityError (email is not unique)
        # userTable.register("tea@hotmail.com", "xxx")
        
        uid = model.user.login("tea@hotmail.com", "xxx")
        model.user.change_password(uid, 'xxx', 'xxxx')
        model.server.register(uid, 'localhost:2050', 'su', 'sp', '', 'hi')
        model.server.change_state(uid, 0)
        model.log.send(uid, 'system', 'message')

        for row in model.user.select():
            print(row)
        for row in model.server.select():
            print(row)
        for row in model.log.select():
            print(row)


##############################################################################

def main(*argv):
    if "server" in argv:
        run_server(*argv[1:])
    elif "test-model" in argv:
        # This should open python shell with loading model object
        test_model()
    elif "shell" in argv:
        print("use python -i option instead")

##############################################################################
if __name__ == '__main__':
    import sys
    # logging.basicConfig(level=logging.INFO)
    main(*sys.argv[1:])
