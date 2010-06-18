#!/bin/sh

err=3
while test "$err" -eq 3 ; do
    python portal.py 0.0.0.0 8080 portal.ini server
    err="$?"
done
