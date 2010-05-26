<?php
##
## JAM FARM PORTAL
##

include_once "ninjam.class.php";

## REQUEST PATTERNS:
#
# * jamfarmportal.php
# * jamfarmportal.php?async=0 (default=1)
# * jamfarmportal.php/test.ninjam.com:2050 (synced)
#

## Manage Interface:
#
# * /register
# * /available/$server/[01]
#

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



