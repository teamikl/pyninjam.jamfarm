
import socket
import struct
import hashlib
from collections import defaultdict

NETMSG_HEADER_LEN = 5

class NetMsg(object):
    __slots__ = 'type', 'data'
    def __init__(self, type, data):
        self.type = type
        self.data = data
        
    def __repr__(self):
        return "<NetMsg type=0x%02X len=%d>" % (self.type, len(self.data))

    def build(self):
        return chr(self.type) + struct.pack('<L', len(self.data)) + self.data

class StopStream(Exception):
    pass

def _parse_header(data):
    if not data:
        raise StopStream
    assert len(data) == NETMSG_HEADER_LEN
    return ord(data[0]), struct.unpack('<L', data[1:])[0]

def _parse_userinfo(stream):
    pos = 0
    datalen = len(stream)
    userlist = defaultdict(dict)
    
    while pos < datalen:
        pos +=6

        next = stream.find('\x00', pos)
        assert next != -1
        nickname = stream[pos:next]
        pos = next+1

        next = stream.find('\x00', pos)
        assert next != -1
        channel = stream[pos:next]
        pos = next+1

        yield nickname, channel

def _read_message_stream(recv):
    try:
        while True:
            msgtype,msglen = _parse_header(recv(NETMSG_HEADER_LEN))
            msgbody = recv(msglen)
            yield NetMsg(msgtype, msgbody)
    except StopStream:
        pass

def _make_passtoken(username, password, challenge):
    passhash = hashlib.sha1("%s:%s" % (username,password))
    passhash = hashlib.sha1(passhash.digest() + challenge)
    return passhash.digest()

class cache(dict):
    """
    Cache get_status result in memory (as python dict)
    """
    def __init__(self, expire):
        self.expire = expire
        
    def __call__(self, func):
        import time
        import functools
        
        @functools.wraps(func)
        def _wrapped(addr, *args, **kw):
            now = time.time()
            if not addr in self or self[addr][0] + self.expire < now:
                self[addr] = (now, func(addr, *args, **kw))
            return self[addr][1]
        
        if __debug__:
            _wrapped._cache = self
        
        return _wrapped

@cache(expire=30)
def get_status(addr, username, password, encoding=None):

    if encoding:
        decode = lambda x: x.decode(encoding).encode('utf-8')
    else:
        decode = lambda x:x

    result = {}
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(addr)
        recv = sock.makefile('rb').read
        send = sock.sendall
        send_msg = lambda _type,_data: send(NetMsg(_type,_data).build())
        
        for msg in _read_message_stream(recv):
            if msg.type == 0x00:
                challenge = msg.data[:8]
                passtoken = _make_passtoken(username, password, challenge)
                chunk = passtoken+username+'\x00'+struct.pack('<LL',1,0x00020000)
                send_msg(0x80, chunk)
            elif msg.type == 0x01:
                print repr(msg.data)
                raise StopStream
            elif msg.type == 0x02:
                bpm,bpi = struct.unpack('<HH', msg.data)
                result['bpm'] = bpm
                result['bpi'] = bpi
            elif msg.type == 0x03:
                userinfo = defaultdict(list)
                for nickname,channel in _parse_userinfo(msg.data):
                    userinfo[nickname].append(channel)
                result['userinfo'] = dict(userinfo)
                
            elif msg.type == 0xC0:
                params = msg.data.split('\x00')
                msgcmd = params[0]
                if msgcmd == 'TOPIC':
                    result['topic'] = decode(params[2])
                elif msgcmd == 'USERCOUNT':
                    pass
            else:
                pass
        sock.close()

    except socket.error, e:
        result['error'] = "not available"
        
    return result


if __name__ == '__main__':
    print get_status(('crasher.orz.hm',8888), 'su', 'sp', encoding='sjis')
    pass