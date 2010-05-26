<?php

# Author: tea
# Since: 2010-03-26


define('MESSAGE_SERVER_AUTH_CHALLENGE', 0x00);
define('MESSAGE_SERVER_AUTH_REPLY', 0x01);
define('MESSAGE_SERVER_CONFIG_CHANGE_NOTIFY', 0x02);
define('MESSAGE_SERVER_USERINFO_CHANGE_NOTIFY', 0x03);
define('MESSAGE_SERVER_DOWNLOAD_INTERVAL_BEGIN', 0x04);
define('MESSAGE_SERVER_DOWNLOAD_INTERVAL_WRITE', 0x05);
define('MESSAGE_CLIENT_AUTH_USER', 0x80);
define('MESSAGE_CLIENT_SET_USERMASK', 0x81);
define('MESSAGE_CLIENT_SET_CHANNEL', 0x82);
define('MESSAGE_CLIENT_UPLOAD_INTERVAL_BEGIN', 0x83);
define('MESSAGE_CLIENT_UPLOAD_INTERVAL_WRITE', 0x84);
define('MESSAGE_CHAT_MESSAGE', 0xC0);
define('MESSAGE_KEEPALIVE', 0xFD);
define('MESSAGE_EXTENDED', 0xFE);
define('MESSAGE_INVALID', 0xFF);

/**
 * string buffer class to handle userinfo notification.
 */
class StringStream
{
    function __construct($buffer)
    {
        $this->pos = 0;
        $this->set_buffer($buffer);
    }

    function set_buffer($buffer)
    {
        $this->buffer = $buffer;
        $this->length = strlen($buffer);
    }

    function read($num)
    {
        $str = substr($this->buffer, $this->pos, $num);
        $this->step(strlen($str));
        return $str;
    }

    function is_empty()
    {
        return ($this->pos == $this->length);
    }

    function step($num)
    {
        $this->pos += $num;
    }

    function next()
    {
        $pos = strpos($this->buffer, "\x00", $this->pos);
        $str = substr($this->buffer, $this->pos, $pos-$this->pos);
        $this->pos = $pos + 1;
        return $str;
    }

}

/**
 * Ninjam protocol message
 *
 *  1 byte    message type
 *  4 bytes   message length
 *  n bytes   message body
 *
 */
class Message
{
    function __construct($msg_type, $chunk)
    {
        $this->type = $msg_type;
        $this->chunk = $chunk;
    }

    function __get($name)
    {
        if ($name == 'length')
        {
            return strlen($this->chunk);
        }
    }

    function __toString()
    {
        return $this->pack();
    }

    function pack()
    {
        return chr($this->type) . pack('V', $this->length) . $this->chunk;
    }
}

class NinjamConnection
{
    var $timeout = 10;

    function __construct()
    {
        $socket = null;
    }

    function connect($host, $port)
    {
        $socket = @fsockopen($host, $port, $errno, $errstr, $this->timeout);
        if (! $socket)
        {
            return false;
        }
        # TODO: stream_set_timeout for async mode

        $this->socket = $socket;

        return true;
    }

    function send_msg($msg)
    {
        return fwrite($this->socket, $msg->pack(), 5+$msg->length);
    }

    function read_msg()
    {
        $chunk = '';
        $buffer = fread($this->socket, 5);
        if (empty($buffer))
        {
            return null;
        }
        $msg_type = ord($buffer[0]);
        $msg_len = array_shift(unpack('V', substr($buffer, 1, 4)));
        if ($msg_len > 0)
        {
            $chunk = fread($this->socket, $msg_len);
        }

        return (new Message($msg_type, $chunk));
    }
}


class NinjamAgent
{
    function __construct()
    {
        $this->connection = null;
    }

    function connect($server, $port)
    {
        $this->connection = new NinjamConnection();
        return $this->connection->connect($server, $port);
    }

    function _make_passhash($username, $password, $challenge)
    {
        $passhash = sha1("$username:$password", true);
        $passhash = sha1("$passhash$challenge", true);
        return $passhash;
    }

    function login($username, $password, $anonymous=true)
    {
        $conn = $this->connection;

        $msg = $conn->read_msg();
        if ($msg->type != MESSAGE_SERVER_AUTH_CHALLENGE || $msg->length < 16)
        {
            return false;
        }
        $challenge = substr($msg->chunk, 0, 8);
        list($servercap,$protoover) = unpack('V2', substr($msg->chunk, 8, 8));
        $license = substr($msg->chunk, 16);

        if ($anonymous)
        {
            $username = "anonymous:$username";
        }
        $passhash = $this->_make_passhash($username, $password, $challenge);
        $chunk = $passhash . $username . "\x00" . pack('V2', 1, 0x00020000);
        $msg = new Message(MESSAGE_CLIENT_AUTH_USER, $chunk);
        $conn->send_msg($msg);

        return true;
    }

    function _parse_server_config($data)
    {
        $tmp = unpack('v2', $data);
        $bpm = $tmp[1];
        $bpi = $tmp[2];
        return array('bpi' => $bpi, 'bpm' => $bpm);
    }

    function _parse_server_userinfo($data)
    {
        $users = array();
        $str = new StringStream($data);
        $len = $msg->length;
        $pos = 0;
        while (! $str->is_empty())
        {
            $str->read(6);
            $username = $str->next();
            $channel = $str->next();

            if (! array_key_exists($username, $users))
            {
                $users[$username] = array();
            }
            if ($channel)
            {
                array_push($users[$username], $channel);
            }
        }
        return $users;
    }

    function read_status()
    {
        $users = array();
        $topic = null;
        $bpm = null;
        $bpi = null;
        
        while ($msg = $this->connection->read_msg())
        {
            switch ($msg->type)
            {
            case MESSAGE_CHAT_MESSAGE:
                $tmp = explode("\x00", $msg->chunk);
                if ($tmp[0] == 'TOPIC')
                {
                    $topic = $tmp[2];
                }
                break;
            case MESSAGE_SERVER_AUTH_REPLY:
                return array('error' => 'invalid login to server');
                break;
            case MESSAGE_SERVER_CONFIG_CHANGE_NOTIFY:
                $tmp = $this->_parse_server_config($msg->chunk);
                $bpm = $tmp['bpm'];
                $bpi = $tmp['bpi'];
                break;
            case MESSAGE_SERVER_USERINFO_CHANGE_NOTIFY:
                $users = $this->_parse_server_userinfo($msg->chunk);
                break;
            default:
                break;
            }
        }

        return array(
            'users' => $users,
            'topic' => $topic,
            'bpi' => $bpi,
            'bpm' => $bpm,
        );
    }
}

/**
 * get_ninjam_status($server, $port, $username, $password)
 *
 *   $username and $password are status user which
 *   set by StatusUserPass in server config.
 *
 */
function get_ninjam_status($server, $port, $username, $password)
{
    $agent = new NinjamAgent();
    if (! $agent->connect($server, $port))
    {
        return array('error' => 'can not connect to server');
    }
    if (! $agent->login($username, $password, false))
    {
        return array('error' => 'login failed');
    }
    return $agent->read_status();
}


# vim: expandtab tabstop=4 shiftwidth=4

