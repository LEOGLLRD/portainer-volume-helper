#!/bin/sh
echo "Installing the dependencies with the requirements file ..."
config/python_env/bin/pip install -r /requirements.txt

/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf