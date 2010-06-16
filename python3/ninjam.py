# -*- coding: utf-8 -*-
# vim: expandtab tabstop=4 shiftwidth=4

"""
 Python Ninjam Network library

 @data: 2010/03/27
 @author: tea
"""

import socket
import struct
import hashlib
import collections
import logging


class InvalidAuthChallengeError(Exception):
    pass

class NETMSG:
    SERVER_AUTH_CHALLENGE = 0x00
    SERVER_AUTH_REPLY = 0x01
    SERVER_CONFIG_CHANGE_NOTIFY = 0x02
    SERVER_USERINFO_CHANGE_NOTIFY = 0x03
    SERVER_DOWNLOAD_INTERVAL_BEGIN = 0x04
    SERVER_DOWNLOAD_INTERVAL_WRITE = 0x05
    CLIENT_AUTH_USER = 0x80
    CLIENT_SET_USERMASK = 0x81
    CLIENT_SET_CHANNEL = 0x82
    CLIENT_UPLOAD_INTERVAL_BEGIN = 0x83
    CLIENT_UPLOAD_INTERVAL_WRITE = 0x84
    CHAT_MESSAGE = 0xC0
    KEEPALIVE = 0xFD
    EXTENDED = 0xFE
    INVALID = 0xFF

class Message:
    def __init__(self, type, data):
        self.type = type
        self.data = data

    def __getattr__(self, key):
        if key == 'length':
            return len(self.data)

    def pack(self):
        return bytes([self.type]) + struct.pack("<L", self.length) + self.data


class Auth:
    def __init__(self, challenge, servercap, protoover, license):
        self.challenge = challenge
        self.servercap = servercap
        self.protoover = protoover
        self.license = license

    @classmethod
    def parse(self, data):
        challenge = data[:8]
        servercap,protoover = struct.unpack('<LL', data[8:16])
        license = data[16:]
        return Auth(challenge, servercap, protoover, license)

class BufferStream:
    def __init__(self, data):
        self.pos = 0
        self.data = data

    def step(self, num):
        self.pos += num

    def empty(self):
        return self.pos >= len(self.data)

    def read_next(self):
        next = self.data.index(b'\x00', self.pos)
        text = self.data[self.pos:next]
        self.pos = next + 1
        return text


class ServerConfig:
    def __init__(self, bpm, bpi):
        self.bpm = bpm
        self.bpi = bpi

    def pack(self):
        return struct.pack('<HH', self.bpm, self.bpi)

    @classmethod
    def parse(self, data):
        return struct.unpack('<HH', data)


class UserInfo:
    @classmethod
    def parse(self, data):
        stream = BufferStream(data)
        while not stream.empty():
            stream.step(6)
            username = stream.read_next().decode('utf-8')
            channel = stream.read_next().decode('utf-8')
            yield username, channel


class Connection:

    TIMEOUT = 3.0

    def __init__(self, host=None, port=None):
        self.conn = None
        self.send = self._dummy_func 
        self.read = self._dummy_func
        if host and port:
            self.connect(host, port)

    def _dummy_func(self, *args):
        raise SystemError('call .connect method first.')
    
    def connect(self, host, port):
        conn = self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.settimeout(self.TIMEOUT)
        conn.connect((host,port))
        self.send = conn.sendall
        self.read = conn.makefile('rb').read
        logging.info('Connected to server {0}:{1}'.format(host,port))

    def read_msg(self):
        tmp = self.read(5)
        if not tmp or len(tmp) < 5:
            return
        msg_type = tmp[0]
        msg_len = struct.unpack('<L', tmp[1:])[0]
        data = self.read(msg_len) if msg_len > 0 else ''
        return Message(msg_type, data)

    def send_msg(self, msg):
        self.send(msg.pack())


class Ninjam(Connection):
    def __init__(self, host, port):
        super(Ninjam, self).__init__(host, port)

    def make_passhash(self, username, password, challenge):
        # cast to bytes Python3 sha1 requires.
        passhash = hashlib.sha1((username + ":" + password).encode('utf-8')).digest()
        passhash = hashlib.sha1(passhash + challenge).digest()
        return passhash + username.encode('utf-8') + b'\x00'

    def read_all_msg(self):
        try:
            while True:
                msg = self.read_msg()
                if msg:
                    yield msg
                else:
                    break
        except socket.error:
            pass

    def login(self, username, password, anonymous=False):
        msg = self.read_msg()
        if msg.type != NETMSG.SERVER_AUTH_CHALLENGE:
            raise InvalidAuthChallengeError()
        if anonymous:
            username = "anonymous:" + username
        auth = Auth.parse(msg.data)
        self.send_auth(username, password, auth.challenge)

    def send_auth(self, username, password, challenge):
        passhash = ninjam.make_passhash(username, password, challenge)
        data = passhash + struct.pack('<LL', 1, 0x00020000)
        self.send_msg(Message(NETMSG.CLIENT_AUTH_USER, data))

    def keepalive(self):
        self.send_msg(Message(NETMSG.KEEPALIVE, b''))


def get_status(host, port, username, password):

    users = collections.defaultdict(list)
    topic = ''
    bpm = bpi = 0

    ninjam = Ninjam(host, port)
    for msg in ninjam.read_all_msg():

        if msg.type == NETMSG.SERVER_AUTH_CHALLENGE:
            auth = Auth.parse(msg.data)
            ninjam.send_auth(username, password, challenge)
            
        elif msg.type == NETMSG.SERVER_AUTH_REPLY:
            raise InvalidAuthReply()

        elif msg.type == NETMSG.SERVER_CONFIG_CHANGE_NOTIFY:
            bpm,bpi = ServerConfig.parse(msg.data)

        elif msg.type == NETMSG.SERVER_USERINFO_CHANGE_NOTIFY:
            for nick,channel in UserInfo.parse(msg.data):
                if channel:
                    users[nick].append(channel)

        elif msg.type == NETMSG.CHAT_MESSAGE:
            tmp = msg.data.split(b'\x00')
            if tmp[0] == b'TOPIC':
                topic = tmp[2].decode('utf-8')

    return dict(bpm=bpm, bpi=bpi, topic=topic, users=users)


if __name__ == '__main__':
    pass
