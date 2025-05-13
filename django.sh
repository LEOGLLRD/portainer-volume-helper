#!/bin/sh
nohup /config/python_env/bin/python /django/manage.py runserver 0.0.0.0:8000 &
pid=$!

/config/python_env/bin/python /django/manage.py makemigrations
/config/python_env/bin/python /django/manage.py migrate

kill $pid
/config/python_env/bin/python /django/manage.py runserver 0.0.0.0:8000