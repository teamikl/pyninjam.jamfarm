# -*- coding: utf-8 -*-

##############################################################################

# TODO: read ../model/portal.sql
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
    INSERT INTO server_table (uid,address,username,password,url,comment) VALUES (?, ?, ?, ?, ?, ?)
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

import sqlite3

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
        self.db.execute(SQL_INSERT_SERVER, (uid,address,username,password,url,comment))

    def unregister(self, id):
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

import string
import random

def _gen_password(length=8, letters=string.letters):
    return ''.join(random.choice(letters) for x in range(length))

##############################################################################

"""
URL MAPPING:

    POST:
        /user/register
        /user/login
        /user/change_password
        /server/register
        /server/update_info
    
    GET:
        /static/
        /json/server_list
        /json/server_info/$address

"""

def _dict2tuple(data, **kw):
    return ((x,data[x]) for x in sorted(data, **kw))

def _unauth(environ, start_response):
    start_response('401 Unauthorized', [('Content-Type','text/plain')])
    return 'Unauthorized'

def _notfound(environ, start_response):
    start_response('404 Not Found', [('Content-Type','text/plain')])
    return 'Not found'

def _notimplemented(environ, start_response):
    start_response('501 NotImplemented', [('Content-Type','text/plain')])
    return 'Not Implemented'

class HTTPErrorResponse(Exception):
    def __init__(self, status, reason=''):
        self.status = status
        self.reason = reason

class URIMapping(object):
    # WSGI URI Mapping middle-ware

    def __init__(self, mapping):
        self.mapping = list(_dict2tuple(mapping, key=len, reverse=True))

    def __call__(self, environ, start_response):
        path_info = environ['PATH_INFO']
        
        for path,app in self.mapping:
            if path_info.startswith(path):
                if path.endswith('/') and path_info[len(path)-1] == '/':
                    environ['PATH_INFO'] = path_info[len(path)-1:]
                return app(environ, start_response)
        else:
            raise HTTPErrorResponse(404)


class Site(object):
    # WSGI application base
    
    error_handlers = {
        401: _unauth,
        404: _notfound,
        500: _notimplemented,
    }

    def __init__(self, get, post):
        self.get = get
        self.post = post

    def __call__(self, environ, start_response):
        try:
            request_method = environ.get('REQUEST_METHOD', None)
            request = HTTPRequest(environ)
            response = HTTPResponse(start_response)
            
            if request_method == 'GET':
                return self.get(environ, start_response)
            elif request_method == 'POST':
                return self.post(environ, start_response)
            else:
                raise HTTPErrorResponse(500)
        except HTTPErrorResponse, e:
            handler = self.error_handlers.get(e.status, _notimplemented)
            environ['_EXCEPTION'] = e.reason
            return [handler(environ, start_response)]

class JamFarmPortal(Site):
    pass

##############################################################################

class HTTPRequest(object):
    def __init__(self, environ):
        self.environ = environ
        
class HTTPResponse(object):
    # TODO: call/cc ?
    def __init__(self, start_response):
        self.start = start_response

# Transform WSGI method call (environ, start_response) -> (request, response)
def content_handler(func):
    import functools
    @functools.wraps(func)
    def _wrapped(self, environ, start_response):
        request = HTTPRequest(environ)
        response = HTTPResponse(start_response)
        return func(self, request, response)
    return _wrapped

class ContentBase(object):
    def __init__(self, model):
        self.model = model


##############################################################################
# Request

class require_auth(object):
    __name__ = 'require_auth'

    def __init__(self, func):
        self.func = func
        
    def __call__(self, self_, request, response):
        if not hasattr(request,'auth') or not request.auth:
            raise HTTPErrorResponse(401)
        return self.func(self_, request, response)


##############################################################################
# Response

class TemplateFactory(object):
    def __init__(self, factory, srcdir):
        self.factory = factory(directories=srcdir)

    def render(self, name):
        template = self.factory.get_template(name)
        def _func(func):
            return lambda self,request,response: template.render(**func(self,request,response))
        return _func

from mako.lookup import TemplateLookup
template = TemplateFactory(TemplateLookup, './templates')


##############################################################################
# Implements Application

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
    @content_handler
    def __call__(self, request, response):
        response.start('200 Ok', [('Content-Type', 'text/plain')])
        yield "OK"

class IndexContent(ContentBase):
    @content_handler
    @template.render('index.html')
    def __call__(self, request, response):
        response.start('200 Ok', [('Content-Type', 'text/html')])
        return {
            'title': 'Index page',
        }

class SiteContainer(object):
    def __init__(self, model):
        self.json = JSONContent(model)
        self.user = UserContent(model)
        self.server = ServerContent(model)
        self.static = StaticContent(model)
        self.index = IndexContent(model)

##############################################################################

def test():
    for i in range(10):
        print(_gen_password())

def test_sv():
    from wsgiref.simple_server import make_server
    
    try:
        site = SiteContainer(Model(Database(':memory:')))
        
        get_mapping = URIMapping({
            '/': site.index,
            '/static/': site.static,
            '/json/server_list': site.json.server_list,
            '/json/server_info': site.json.server_info,
        })
        post_mapping = URIMapping({
            '/user/register': site.user.register,
            '/user/login': site.user.login,
            '/user/change_password': site.user.change_password,
            '/server/register': site.server.register,
            '/server/update_info': site.server.update_info,
        })
        
        app = JamFarmPortal(get_mapping, post_mapping)
        server = make_server('', 8000, app)
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


def test_db():
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
    # TEST CODE:
    if "test" in argv:
        test()
    elif "server" in argv:
        test_sv()
    elif "model" in argv:
        test_db()

##############################################################################
if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
