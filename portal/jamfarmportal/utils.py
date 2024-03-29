
import re
import string
import random

def generate_password( length=8, token=string.digits+string.letters):
    return ''.join(random.choice(token) for x in xrange(length))

def is_valid_email(email):
    # XXX: use re.match
    return email.count('@') == 1
