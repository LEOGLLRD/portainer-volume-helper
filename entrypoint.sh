#!/bin/sh

# First installing the dependencies with the requirements.txt file
echo "Installing the dependencies with the requirements file ..."
config/python_env/bin/pip install -r /requirements.txt

echo "Launching Django ..."
nohup /config/python_env/bin/python /django/manage.py runserver 0.0.0.0:8000 &
pid=$!
/config/python_env/bin/python /django/manage.py makemigrations
/config/python_env/bin/python /django/manage.py migrate
kill $pid
/config/python_env/bin/python /django/manage.py runserver 0.0.0.0:8000


