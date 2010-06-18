@echo off
:repeat
    python portal.py server 0.0.0.0 8080 portal.ini
if %errorlevel% == 3 goto repeat