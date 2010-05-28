<?php
##
## JAM FARM PORTAL
##

include_once "ninjam.class.php";

## REQUEST PATTERNS:
#
# * jamfarm_portal.php (index)
# * jamfarm_portal.php/test.ninjam.com:2050
#

## Manage Interface:
#
# * /register
# * /enable/$server/[01]
# * /disable/
# * /add/
# * /del/

## RETURN VALUE:
#
# [
#    {'server': 'test.ninjam.com:2050',
#     'topic': '',
#     'users': [
#       {'nick': 'test', 'channels': ['guitar L','guitar R']},
#     ]
#     'atime': '(accessed time)'
#     'state': 0,
#    },
#    {'server': 'test.ninjam.com:2050',
#     'state': 1,
#    },
#    {'server': 'example.com:2050',
#     'error': 'cant connect',
#     'state': 2,
#    }
# ]

## ERRORS:
#
# * Can not connect to the host
#

# TODO: Check Cache in DB

# TODO: Build JSON data

# TODO: Return JSON format

# TODO: stream_select for async

# TODO: OpenID
