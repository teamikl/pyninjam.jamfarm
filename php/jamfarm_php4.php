<?php

# vim: expandtab tabstop=4 shiftwidth=4

# error_reporting(E_ALL);

function recv_msg($stream)
{
    $buffer = fread($stream, 5);
    if (! $buffer || strlen($buffer) < 5)
        return null;
    $msg_type = ord($buffer[0]);
    $msg_length = array_shift(unpack('V', substr($buffer, 1, 4)));
    $data = ($msg_length > 0) ? fread($stream, $msg_length) : '';
    return array('type' => $msg_type, 'length' => $msg_length, 'data' => $data);
}

function send_msg($stream, $type, $data)
{
    return fwrite($stream, chr($type) . pack('V', strlen($data)) . $data);
}

function parse_auth_challenge($data)
{
    $challenge = substr($data, 0, 8);
    list($servercap,$protoover) = array_values(unpack('V2', substr($data, 8, 8)));
    $license = substr($data, 16);
    return array('challenge' => $challenge, 'license' => $license);
}

function &parse_userinfo($data)
{
    $users = array();
    $pos = 0;

    while ($tmp = substr($data, $pos, 6)) {
        $pos += 6;
        $next = strpos($data, "\x00", $pos);
        $username = substr($data, $pos, $next-$pos);
        $pos = $next + 1;
        $next = strpos($data, "\x00", $pos);
        $channel = substr($data, $pos, $next-$pos);
        $pos = $next + 1;

        if (! array_key_exists($username, $users))
            $users[$username] = array();
        if ($channel)
            array_push($users[$username], $channel);
    }
    return $users;
}

function make_passhash($username, $password, $challenge)
{
    $passhash = pack('H*', sha1("$username:$password"));
    $passhash = pack('H*', sha1("$passhash$challenge"));
    return $passhash . $username . "\x00" . pack('V2', 1, 0x00020000);
}

function get_ninjam_status($host, $port, $username, $password)
{
    $socket = @fsockopen($host, $port, $errno, $errstr, 30);
    if (! $socket)
        return array('error' => $errstr);
    $msg = recv_msg($socket);
    if ($msg['type'] != 0x00 || $msg['length'] < 16)
	return array('error' => 'invalid auth challenge');

    $auth = parse_auth_challenge($msg['data']);
    send_msg($socket, 0x80, make_passhash($username, $password, $auth['challenge']));


    $users = array();
    $bpm = $bpi = 0;
    $topic = '';

    while ($msg = recv_msg($socket)) {
        switch ($msg['type']) {
        case 0x01:
            return array('error' => 'invalid auth reply');
        case 0x02:
            list($bpm,$bpi) = array_values(unpack('v2', $msg['data']));
            break;
	case 0x03:
            $users = parse_userinfo($msg['data']);
            break;
        case 0xC0:
            $tmp = explode("\x00", $msg['data']);
            if ($tmp[0] == 'TOPIC')
                $topic = $tmp[2];
            break;
        }
    }
    fclose($socket);

    return array(
      'topic' => $topic,
      'users' => $users,
      'bpm' => $bpm,
      'bpi' => $bpi,
    );
}

function _htmlspecialchars($text)
{
    return htmlspecialchars($text, ENT_QUOTES, 'SJIS');
}

function main($host, $port, $username, $password)
{
    # For PHP4 compatibility
    # define those function to use cache. PHP manual has samplpe implementations.
    if (function_exists('file_get_contents') && function_exists('file_put_contents')) {
      $cache_expire = time() - 10;                   # -10 for 10 seconds cache expired time.
      $cache_file = "${host}_${port}_status.cache";  # cache file, must be unique each host:port.

      if (is_file($cache_file)) {
        $cache_stat = @stat($cache_file);
        if ($cache_stat && $cache_stat['mtime'] > $cache_expire) {
           $status = unserialize(file_get_contents($cache_file));
        }
      }
      if (! isset($status)) {
        $status = get_ninjam_status($host, $port, $username, $password);
        file_put_contents($cache_file, serialize($status));
      }
    }
    else {
      # No use cache
      $status = get_ninjam_status($host, $port, $username, $password);
    }

    if (array_key_exists('error', $status)) {
      echo "<p>", _htmlspecialchars($status['error']), "</p>\n";
      return 1;
    }

    $bpm = $status['bpm'];
    $bpi = $status['bpi'];
    $topic = _htmlspecialchars($status['topic']);
    $count = count($status['users']);

    echo "<dl>",
         "<dt>Server</dt><dd>$host:$port</dd>",
         "<dt>Topic</dt><dd>",_htmlspecialchars($topic),"</dd>",
         "<dt>BPM</dt><dd>$bpm</dd>",
         "<dt>BPI</dt><dd>$bpi</dd>",
         "</dl>\n";

    if ($count > 0) {
      echo "<ul>\n";
      foreach ($status['users'] as $name => $channels) {
        echo "  <li>", _htmlspecialchars($name);
        if (count($channels) > 0) {
          echo " (", join(", ", array_map('_htmlspecialchars', $channels)), ")";
        }
        echo "</li>\n";
      }
      echo "</ul>\n";
    }
    else {
      echo "<p>No users</p>\n";
    }

    return 0;
}


header('Cache-Control: no-cache, must-revalidate');
header('Pragma: no-cache');

# Win32/Japanese
# header('Content-Type: text/html; charset=Shift_JIS');

exit(main('127.0.0.1', 2050, 'status', 'status'));

