
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(128), unique=True)
    password = Column(String(16), unique=True)
    created = Column(DateTime, default=datetime.now())

    def __init__(self, email=None, password=None):
        self.email = email
        self.password = password
    
    def __repr__(self):
        return "<User %r>" % self.email

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True)
    owner = Column(Integer, ForeignKey('users.id'))
    server = Column(String(32), unique=True)
    username = Column(String(16), nullable=False)
    password = Column(String(16), nullable=False)
    comment = Column(String(140))
    website = Column(String(256))
    created = Column(DateTime, default=datetime.now())

    @property
    def name(self):
        # for HTML id
        return self.server.replace(':','.')

    def __init__(self, owner, server, username, password, comment="", website=""):
        self.owner = owner
        self.server = server
        self.comment = comment
        self.website = website
        self.username = username
        self.password = password

    def __repr__(self):
        return "<Site %r>" % self.server
        