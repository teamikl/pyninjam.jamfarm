# -*- coding: utf-8 -*-

##############################################################################

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
        /
        /json/server_list
        /json/server_info/$address

"""

class Site(dict):
    def __init__(self, model):
        self.model = model


class JamFarmPortal(object):

    def __init__(self, site, config):
        self.site = site
        self.config = config

    def __call__(self, environ, start_response):
        request_method = environ.get('REQUEST_METHOD', None)
        if request_method == 'GET':
            # TODO
            pass
        elif request_method == 'POST':
            # TODO
            pass
        else:
            start_response('501 NotImplemented', [('Content-Type','text/plain')])
            return 'Not Implemented'


##############################################################################


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
    test_db()

##############################################################################
if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
